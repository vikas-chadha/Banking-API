from curses.ascii import US
from random import random
from api.models.transactionModel import Transaction
from api.serializers.bankings.bankSerializers import TransactionSerializer
from rest_framework import status
from api.utils.messages.commonMessages import *
from api.utils.messages.roleMessages import *
from api.utils.messages.bankingsMessage import *
from django.db.models import Q
from .bankingsBaseService import BankingsBaseService
from api.models import *
from api.serializers.bankings import CreateUpdateBankAccountSerializer, GetBankAccountSerializer, GetBankSerializer
import random
from api.utils.createTransaction import create_transaction

class BankingsService(BankingsBaseService):
    """
    These Services Class contains all the Business Logics
    """

    def __init__(self):
        pass
    
    def create_bank_account(self, request, format=None):
        request.data['user'] = request.user.id

        unique = False
        while unique is False:
            try:
                bank_obj = Bank.objects.get(id = request.data['bank'])
            except Bank.DoesNotExist:
                return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
            account_number = self.generate_random_account_number(bank_obj.bank_name)
            res = self.check_unique(account_number)
            if res is True:
                unique = True
        request.data['account_number'] = account_number
        serializer = CreateUpdateBankAccountSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            self.set_default_bank_account(request.user.id)
            return ({"data": serializer.data, "code": status.HTTP_201_CREATED, "message": BANK_ACCOUNT_CREATED})
        return ({"data": serializer.errors, "code": status.HTTP_400_BAD_REQUEST, "message": BAD_REQUEST})
    
    def get_bank_account(self, request, pk, format=None):
        try:
            acc_obj = BankAccount.objects.get(id = pk, user = request.user.id)
        except:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        serializer = GetBankAccountSerializer(acc_obj)
        return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": BANK_ACCOUNT_FETCHED})

    def get_all_bank_account(self, request, format=None):
        acc_obj = BankAccount.objects.filter(user = request.user.id)
        serializer = GetBankAccountSerializer(acc_obj, many=True)
        return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": BANK_ACCOUNT_FETCHED})

    def update_bank_account(self, request, pk, format=None):
        try:
            acc_obj = BankAccount.objects.get(id = pk)
        except:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        serializer = GetBankAccountSerializer(acc_obj, data = request.data)
        if serializer.is_valid():
            serializer.save()
            return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": BANK_ACCOUNT_UPDATED})
        return ({"data": serializer.errors, "code": status.HTTP_400_BAD_REQUEST, "message": BAD_REQUEST})

    def delete_bank_account(self, request, pk, format=None):
        try:
            acc_obj = BankAccount.objects.get(id = pk)
        except:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})

        all_acc = BankAccount.objects.filter(user = request.user.id)
        if len(all_acc) > 0:
            all_acc = all_acc[0]
            all_acc.is_default = True
            all_acc.save()

        acc_obj.delete()
        return ({"data": None, "code": status.HTTP_200_OK, "message": BANK_ACCOUNT_DELETED})

    def set_primary_account(self, request, bank_account_id, format=None):
        user_id = request.user.id
        try:
            bank_obj = BankAccount.objects.get(id = bank_account_id, user=user_id)
        except BankAccount.DoesNotExist:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        
        if bank_obj.user.id != user_id:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        
        bank_objs = BankAccount.objects.filter(user = user_id)
        bank_objs.update(is_default = False)

        bank_obj.is_default = True
        bank_obj.save()
        return ({"data": None, "code": status.HTTP_200_OK, "message": OK})


    def get_bank(self, request, pk, format=None):
        try:
            acc_obj = Bank.objects.get(id = pk)
        except:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        serializer = GetBankSerializer(acc_obj)
        return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": BANK_ACCOUNT_FETCHED})

    def get_all_bank(self, request, format=None):
        acc_obj = Bank.objects.all()
        serializer = GetBankSerializer(acc_obj, many=True)
        return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": BANK_ACCOUNT_FETCHED})

    def send_money(self, request, format=None):
        sender_id = request.user.id
        recipient_id = request.data.get('recipient_id')
        try:
            recipient_obj = User.objects.get(id = recipient_id)
        except User.DoesNotExist:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": RECORD_NOT_FOUND})
        from_bank_account = request.data.get('from_bank_account')
        amount = request.data.get('amount')
        try:
            sender_bank_obj = BankAccount.objects.get(id = from_bank_account)
            if sender_bank_obj.user.id != sender_id:
                return ({"data": "Sender's Bank Does Not Exists.", "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        except BankAccount.DoesNotExist:
            return ({"data": "Sender's Bank Does Not Exists.", "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        
        try:
            recipient_bank = BankAccount.objects.get(user=recipient_id, is_default = True)
        except BankAccount.DoesNotExist:
            return ({"data": "Recipients's Bank Does Not Exists.", "code": status.HTTP_400_BAD_REQUEST, "message": BANK_NOT_FOUND})
        
        sender_bank_obj.balance = float(sender_bank_obj.balance) - float(amount)
        
        if sender_bank_obj.balance < 0.0:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": INSUFFICIENT_BALANCE})

        if sender_bank_obj.id == recipient_bank.id:
            return ({"data": "You cannot send money to the same bank account.", "code": status.HTTP_400_BAD_REQUEST, "message": CIRULAR_TRANSFER})
        
        sender_bank_obj.save()
        recipient_bank.balance = float(recipient_bank.balance) + float(amount)
        recipient_bank.save()

        create_transaction(request.user,recipient_obj, amount, sender_bank_obj, recipient_bank)
        return ({"data": None, "code": status.HTTP_200_OK, "message": TRANSFER_SUCCESSFULL})

    def transaction_list(self, request, format=None):
        tran_obj = Transaction.objects.filter(Q(sender=request.user.id) | Q(reciever=request.user.id))
        serializer = TransactionSerializer(tran_obj, many=True, context = {"request":request})
        return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": TRANSACTION_FETCHED})

    def get_transaction_by_id(self, request, pk, format=None):
        try:
            tran_obj = Transaction.objects.filter(id = pk)
        except Transaction.DoesNotExist:
            return ({"data": None, "code": status.HTTP_400_BAD_REQUEST, "message": TRANSACTION_NOT_FOUND})
        serializer = TransactionSerializer(tran_obj, many=True, context = {"request":request})
        return ({"data": serializer.data, "code": status.HTTP_200_OK, "message": TRANSACTION_FETCHED})
    
    
    
    
    #Helper Functions

    def generate_random_account_number(self, bank_name):
        print(bank_name)
        account_number = bank_name + str(random.randint(1111111111,9999999999))
        return account_number


    def check_unique(self, account_number):
        try:
            exiting_obj = BankAccount.objects.get(account_number = account_number)
        except BankAccount.DoesNotExist:
            return True
        return False

    def set_default_bank_account(self, user_id):
        bank_obj = BankAccount.objects.filter(user = user_id)
        if len(bank_obj) == 1:
            bank_obj.update(is_default = True)
            return True
        return False

        

    

        
    
        
        
    
    
