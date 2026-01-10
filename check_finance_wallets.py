from finance.models import Transaction, Wallet

def check_txns():
    print("All Transactions:")
    for t in Transaction.objects.all():
        dest = t.destination_wallet
        owner = dest.owner if dest else "None"
        print(f"Type: {t.transaction_type} | Amount: {t.amount_display} | Owner: {owner} | ID: {t.id}")
        
    print("\nAll Wallets:")
    for w in Wallet.objects.all():
        print(f"Owner: {w.owner} | Available: {w.available_balance} | Liability: {w.liability_balance} | Escrow: {w.escrow_balance}")

if __name__ == "__main__":
    check_txns()
