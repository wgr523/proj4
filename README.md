How to run:
python3 primary_server.py 1
1 �� ���������룬Ŀǰֻ֧��123��
����conf�������ip��ַ��

How to test:
run server 1 and 2, don't run 3. Do many insert to server 1 (or 2).
��Ϊ2������һ�룬���Բ������������ġ�
then run server 3, in server 3, do something (insert).
then check everyone's /kvman/countkey (or dump), server 1,2,3 should be the same

Also, you can go to /kvman/kvpaxos to see the sequence of paxos. E.g., run 10 insert and then see localhost:8001/kvman/kvpaxos ������������ÿ�һЩ��
