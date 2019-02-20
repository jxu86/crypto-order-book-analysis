import smtplib
from email.mime.text import MIMEText
 

class EmailService(object):
    def __init__(self):
        # 第三方 SMTP 服务
        self.mail_host = 'smtp.qq.com'  # SMTP服务器
        self.mail_user = '641750707@qq.com'  # 用户名
        self.mail_pass = 'uzgokdmiecacbbcg'  # 授权码
        self.sender = '641750707@qq.com'
        self.receivers = ['641750707@qq.com', 'yuiant@qq.com', 'no7david@gmail.com', 'jhuang1@kalengo.com']  # 接收人邮箱
    
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

def main():
    e = EmailService()
    e.send('python test', 'hellooooooooo!!!!!')


if __name__ == '__main__':
    main()

