from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from .models import Wallet, Transaction, EscrowEntry, CODSettlementRequest
from .services import FinanceService
from django.contrib import messages
from django.db.models import Q
from business_partners.models import BusinessPartner
from decimal import Decimal
from business_partners.utils import get_user_currency
from parts.models import Order, OrderItem
from vendor_employees.utils import get_vendor_context
from vendor_employees.permissions import vendor_permission_required

@login_required
def user_wallet_view(request):
    """View for user's personal wallet and transactions."""
    user_ct = ContentType.objects.get_for_model(request.user)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=user_ct,
        owner_id=request.user.id,
        defaults={'currency': 'USD'}
    )
    
    # Get transactions where this wallet is either source or destination
    transactions = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('-created_at')
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'user/finance/wallet.html', context)

@login_required
def transaction_detail_view(request, transaction_id):
    """View for transaction details."""
    user_ct = ContentType.objects.get_for_model(request.user)
    wallet = get_object_or_404(Wallet, owner_content_type=user_ct, owner_id=request.user.id)
    
    transaction = get_object_or_404(
        Transaction, 
        Q(id=transaction_id) & (Q(source_wallet=wallet) | Q(destination_wallet=wallet))
    )
    
    context = {
        'transaction': transaction,
        'wallet': wallet,
    }
    return render(request, 'user/finance/transaction_detail.html', context)

@login_required
@vendor_permission_required('finance', action='view')
def vendor_wallet_view(request):
    """View for vendor's business wallet and transactions."""
    # Find the BusinessPartner for this user (master or employee)
    vendor = get_vendor_context(request.user)
    
    if not vendor:
        return redirect('users:user-dashboard')
        
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet, created = Wallet.objects.get_or_create(
        owner_content_type=vendor_ct,
        owner_id=vendor.id,
        defaults={'currency': 'USD'}
    )
    
    # Get transactions where this wallet is either source or destination
    transactions = Transaction.objects.filter(
        Q(source_wallet=wallet) | Q(destination_wallet=wallet)
    ).order_by('-created_at')
    
    # Get escrow entries
    escrow_entries = EscrowEntry.objects.filter(wallet=wallet, is_released=False).order_by('release_date')

    payment_transactions = transactions.filter(destination_wallet=wallet, transaction_type='PAYMENT')
    order_ids = set()
    for txn in payment_transactions:
        order_id = (txn.metadata or {}).get('order_id')
        if order_id:
            order_ids.add(order_id)

    cod_order_ids = set()
    if order_ids:
        cod_order_ids = set(
            Order.objects.filter(id__in=order_ids, payment_method='cash_on_delivery').values_list('id', flat=True)
        )

    cod_cash_received = Decimal('0.00')
    if cod_order_ids:
        for txn in payment_transactions:
            order_id = (txn.metadata or {}).get('order_id')
            if order_id in cod_order_ids:
                cod_cash_received += (txn.amount_base or Decimal('0.00'))

    total_earnings = (wallet.available_balance or Decimal('0.00')) + (wallet.escrow_balance or Decimal('0.00')) + cod_cash_received
    
    context = {
        'vendor': vendor,
        'wallet': wallet,
        'transactions': transactions,
        'escrow_entries': escrow_entries,
        'cod_cash_received': cod_cash_received,
        'total_earnings': total_earnings,
    }
    return render(request, 'user/finance/vendor/wallet.html', context)

@login_required
@vendor_permission_required('finance', action='view')
def vendor_transaction_detail_view(request, transaction_id):
    """View for vendor's business transaction details."""
    # Find the BusinessPartner for this user (master or employee)
    vendor = get_vendor_context(request.user)
    
    if not vendor:
        return redirect('users:user-dashboard')
        
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet = get_object_or_404(Wallet, owner_content_type=vendor_ct, owner_id=vendor.id)
    
    transaction = get_object_or_404(
        Transaction, 
        Q(id=transaction_id) & (Q(source_wallet=wallet) | Q(destination_wallet=wallet))
    )
    
    # Calculate consolidated details if order-related
    item_ct = ContentType.objects.get_for_model(OrderItem)
    consolidated_data = None
    
    if transaction.transaction_type in ['PAYMENT', 'COMMISSION'] and transaction.reference_id and transaction.reference_content_type == item_ct:
        item_id = transaction.reference_id
        
        # Find related transactions for this item
        item_txs = Transaction.objects.filter(
            reference_content_type=item_ct,
            reference_id=item_id
        )
        
        payment_tx = item_txs.filter(transaction_type='PAYMENT').first()
        commission_tx = item_txs.filter(transaction_type='COMMISSION').first()
        
        # Settlement Amount
        amount_settled = payment_tx.amount_base if payment_tx else Decimal('0.00')
        
        # Commission and Tax
        commission_val = Decimal('0.00')
        tax_val = Decimal('0.00')
        
        if commission_tx:
            try:
                commission_val = Decimal(str(commission_tx.metadata.get('commission', '0.00')))
                tax_val = Decimal(str(commission_tx.metadata.get('tax', '0.00')))
            except (ValueError, TypeError):
                pass
        
        # Order Amount
        order_amount = Decimal('0.00')
        if payment_tx and payment_tx.reference:
            try:
                order_amount = payment_tx.reference.total_price
            except:
                order_amount = amount_settled + commission_val + tax_val
        else:
            order_amount = amount_settled + commission_val + tax_val

        consolidated_data = {
            'order_number': transaction.order_number or "N/A",
            'order_amount': order_amount,
            'tax': tax_val,
            'commission': -commission_val,
            'amount_settled': amount_settled,
            'is_settlement': True
        }
    
    context = {
        'transaction': transaction,
        'wallet': wallet,
        'vendor': vendor,
        'consolidated_data': consolidated_data,
    }
    return render(request, 'user/finance/vendor/transaction_detail.html', context)

@login_required
@vendor_permission_required('finance', action='create')
def submit_cod_settlement(request):
    """View for vendors to submit COD settlement proof."""
    vendor = get_vendor_context(request.user)
    
    if not vendor:
        return redirect('users:user-dashboard')
        
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet = get_object_or_404(Wallet, owner_content_type=vendor_ct, owner_id=vendor.id)
    
    if request.method == 'POST':
        amount_raw = request.POST.get('amount')
        reference = request.POST.get('reference_number')
        evidence = request.FILES.get('evidence_image')
        
        if not amount_raw or not reference:
            messages.error(request, "Amount and reference number are required.")
        else:
            try:
                submitted_amount = Decimal(str(amount_raw))
            except Exception:
                submitted_amount = Decimal('0.00')

            if submitted_amount <= 0:
                messages.error(request, "Amount must be greater than zero.")
                return render(request, 'user/finance/vendor/submit_settlement.html', {'wallet': wallet})

            currency_code = None
            session = getattr(request, 'session', None)
            if session is not None:
                currency_code = session.get('currency_code')
            if not currency_code and getattr(request, 'currency', None):
                currency_code = getattr(request.currency, 'code', None)
            if not currency_code:
                currency_code = get_user_currency(request.user)
            currency_code = (currency_code or 'SAR').upper()

            amount_usd = submitted_amount
            if currency_code != 'USD':
                try:
                    from core.models import ExchangeRate
                    rate_to_usd = Decimal(str(ExchangeRate.get_current_rate(currency_code, 'USD')))
                    amount_usd = (submitted_amount * rate_to_usd).quantize(Decimal('0.01'))
                except Exception:
                    messages.error(request, "Unable to convert currency. Please try again.")
                    return render(request, 'user/finance/vendor/submit_settlement.html', {'wallet': wallet})

            if amount_usd > wallet.liability_balance:
                messages.error(request, "Settlement amount exceeds your outstanding liability.")
                return render(request, 'user/finance/vendor/submit_settlement.html', {'wallet': wallet})

            CODSettlementRequest.objects.create(
                vendor=vendor,
                wallet=wallet,
                amount=amount_usd,
                reference_number=reference,
                evidence_image=evidence
            )
            messages.success(request, "Settlement request submitted successfully and is pending review.")
            return redirect('business_partners:vendor_finance_dashboard')
            
    return render(request, 'user/finance/vendor/submit_settlement.html', {'wallet': wallet})

@login_required
def admin_cod_settlements(request):
    """View for admins to review and process COD settlements."""
    if not request.user.is_staff:
        return redirect('dashboard')
        
    status_filter = request.GET.get('status', 'pending')
    requests = CODSettlementRequest.objects.filter(status=status_filter).order_by('-created_at')
    
    if request.method == 'POST':
        request_id = request.POST.get('request_id')
        action = request.POST.get('action') # 'approved' or 'rejected'
        notes = request.POST.get('notes', '')
        
        settlement_req = get_object_or_404(CODSettlementRequest, id=request_id)
        
        try:
            FinanceService.process_cod_settlement(
                settlement_req, 
                action, 
                request.user, 
                notes
            )
            messages.success(request, f"Settlement request {action} successfully.")
        except Exception as e:
            messages.error(request, f"Error processing settlement: {str(e)}")
            
        return redirect('finance:admin_cod_settlements')
        
    return render(request, 'admin_panel/finance/cod_settlements.html', {'settlement_requests': requests, 'status_filter': status_filter})

@login_required
def request_payout(request):
    """View for vendors to request a payout of their available balance."""
    vendor = get_object_or_404(BusinessPartner, user=request.user)
    if not vendor.is_vendor():
        return JsonResponse({'success': False, 'message': 'Only vendors can request payouts.'}, status=403)
        
    vendor_ct = ContentType.objects.get_for_model(vendor)
    wallet = get_object_or_404(Wallet, owner_content_type=vendor_ct, owner_id=vendor.id)
    
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            amount = Decimal(str(data.get('amount', 0)))
            
            if amount <= 0:
                return JsonResponse({'success': False, 'message': 'Amount must be greater than zero.'})
                
            if amount > wallet.available_balance:
                return JsonResponse({'success': False, 'message': 'Insufficient available balance.'})
                
            # Check if bank details are set
            from business_partners.models import VendorProfile
            try:
                profile = vendor.vendor_profile
            except VendorProfile.DoesNotExist:
                profile = VendorProfile.objects.create(business_partner=vendor, user=request.user)
            if not profile.bank_name or not profile.bank_account_number:
                return JsonResponse({'success': False, 'message': 'Please update your bank details in profile settings before requesting a payout.'})
            
            # Record the payout using FinanceService
            # Note: This will deduct from available balance and create a PENDING transaction
            FinanceService.record_payout(vendor, amount, processed_by=request.user)
            
            return JsonResponse({
                'success': True, 
                'message': 'Payout request submitted successfully. It will be processed according to the schedule.'
            })
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
            
    return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)
