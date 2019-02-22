import smtplib
from email.mime.text import MIMEText
 

class EmailService(object):
    def __init__(self):
        # 第三方 SMTP 服务
        self.mail_host = 'smtp.qq.com'  # SMTP服务器
        self.mail_user = '641750707@qq.com'  # 用户名
        self.mail_pass = 'uzgokdmiecacbbcg'  # 授权码
        self.sender = '641750707@qq.com'
        self.receivers = ['641750707@qq.com']  # 接收人邮箱
    
    def send(self, title, content):
        message = MIMEText(content, 'plain', 'utf-8')  # 内容, 格式, 编码
        message['From'] = '{}'.format(self.sender)
        message['To'] = ','.join(self.receivers)
        message['Subject'] = title
        try:
            smtpObj = smtplib.SMTP_SSL(self.mail_host, 465)  # 启用SSL发信, 端口一般是465
            smtpObj.login(self.mail_user, self.mail_pass)  # 登录验证
            smtpObj.sendmail(self.sender, self.receivers, message.as_string())  # 发送
            print('mail has been send successfully.')
        except smtplib.SMTPException as e:
            print('send email err=>', e)

    def sumit_order(self, order_info):
        status = order_info['status']
        otype = order_info['type']
        if status == '-1':
            status = 'canceled'
        elif status == '0':
            status = 'pending'
        elif status == '1':
            status = 'partially filled'
        elif status == '2':
            status = 'pendfully filleding'
        
        if otype == '1':
            otype = 'open long'
        elif otype == '2':
            otype = 'open short'
        elif otype == '3':
            otype = 'close long'
        elif otype == '2':
            otype = 'close short'

        title = 'EMA stratery: sumit order '+order['timestamp']
        content = 'instrument_id:{instrument_id}\norder id:{order_id}\ntype:{type}\norder size:{size}\ntime:{time}\nstatus:{status}\nfee:{fee}'.format(
            instrument_id=order_info['instrument_id'],
            order_id=order_info['order_id'],
            type=otype,
            size=order_info['size'],
            time=order_info['timestamp'],
            status=status,
            fee=order_info['fee'])
            
        self.send(title, content)
    
    # def canel_order(self, order_info)

def main():
    e = EmailService()
    order_id = '1232132'
    amount = 100
    content = 'order id:{order_id}\norder amount:{amount}'.format(order_id=order_id,amount=amount)
    e.send('EMA stratery: sumit order', content)


if __name__ == '__main__':
    main()

