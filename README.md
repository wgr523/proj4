How to run:
python3 primary_server.py 1
1 是 服务器号码，目前只支持123。
看看conf，里边有ip地址。

How to test:
run server 1 and 2, don't run 3. Do many insert to server 1 (or 2).
因为2个超过一半，所以操作都是正常的。
then run server 3, in server 3, do something (insert).
then check everyone's /kvman/countkey (or dump), server 1,2,3 should be the same

Also, you can go to /kvman/kvpaxos to see the sequence of paxos. E.g., run 10 insert and then see localhost:8001/kvman/kvpaxos （用浏览器看好看一些）
