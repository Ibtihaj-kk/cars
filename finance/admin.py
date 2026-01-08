from django.contrib import admin
from .models import Wallet, Transaction, EscrowEntry

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('owner', 'available_balance', 'escrow_balance', 'liability_balance', 'currency')
    list_filter = ('currency', 'is_active')
    search_fields = ('owner_id',)
    readonly_fields = ('available_balance', 'escrow_balance', 'liability_balance')

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'transaction_type', 'amount_base', 'currency', 'source_wallet', 'destination_wallet', 'created_at')
    list_filter = ('transaction_type', 'currency', 'created_at')
    search_fields = ('metadata', 'reference_id')
    readonly_fields = ('created_at',)

@admin.register(EscrowEntry)
class EscrowEntryAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'amount', 'release_date', 'is_released')
    list_filter = ('is_released', 'release_date')
    search_fields = ('wallet__owner_id',)
