# 个人 AWS 部署与作业提交

## 作业需要完成什么

1. 完成 Django 5.2 官方教程第 1、2、3、4 部分，形成可投票的 polls 应用。
2. 代码提交到自己的 GitHub 仓库，名字必须是 `swe1-app`。
3. 部署到自己的 AWS 账号，让老师能直接打开 `/polls/`、投票、查看结果。
4. 在下一次 live session 之前，在 Brightspace 对应作业提交应用 URL 和 GitHub URL。
   具体 session 时间以课程安排为准；题目没有给出具体日期。
5. 评分完成前保持网站可访问。迟交会影响成绩。

课程 PDF 的末尾保留了团队账号的旧说明；本次题目明确是个人作业，因此使用个人账号。
实现依据：https://docs.djangoproject.com/en/5.2/intro/tutorial01/
AWS 部署依据：https://docs.aws.amazon.com/elasticbeanstalk/latest/dg/create-deploy-python-django.html

## 1. 创建个人账号（需要本人完成）

打开 https://aws.amazon.com/free/ ，选择创建账号，填写本人邮箱、联系人和付款验证信息，
完成邮箱、手机验证及账号激活。密码、验证码、银行卡信息和 Access Key 不要发送到聊天里。
选择 **Free plan**，避免误选付费套餐或付费支持计划。

截至 2026-10-11，AWS 官方规则是：新用户初始获得 $100 credits，完成指定活动最多再获
$100；Free plan 最长 6 个月或额度用完时结束。保持 Free plan、不升级或启用付费专属服务，
不会产生付费账单。账号自身免费，但服务器会消耗额度。最小 EB 单实例配置的官方估算约
$12/月，实际取决于区域、存储、网络流量和配置。部署前在 Billing 中确认你的实际计划和额度。

费用来源：
- https://aws.amazon.com/free/
- https://aws.amazon.com/elasticbeanstalk/pricing/

本项目选择单实例 `t3.micro`，不创建负载均衡器、RDS 或 NAT Gateway。
不要开启额外服务来完成本作业。可在 Billing / Budgets 设置预算提醒；提醒不会自动停止资源。

## 2. 登录本机 AWS CLI

本机已安装 AWS CLI v2，支持浏览器临时登录，不需要手动创建长期 Access Key。
在 PowerShell 中运行，并在浏览器中由本人完成登录：

```powershell
aws login --region us-east-1
aws sts get-caller-identity --region us-east-1
```

若注册后仍未激活，请先等待账号激活。登录说明：
https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html

## 3. 安装独立 EB CLI

在本项目目录运行。EB CLI 放在单独环境，避免其依赖混入应用的 `requirements.txt`。

```powershell
.\.venv\Scripts\python.exe -m venv .ebcli-venv
.\.ebcli-venv\Scripts\python.exe -m pip install awsebcli
.\.ebcli-venv\Scripts\eb.exe --version
```

## 4. 部署

```powershell
.\.venv\Scripts\python.exe scripts\deploy.py --region us-east-1
```

脚本会核对当前个人账号，选择该区域支持的 Python 3.12 / Amazon Linux 2023 平台，
创建所需 EB service role 和 EC2 instance profile，配置 SSH key，检查默认 VPC，
构建 ZIP，通过 `eb init` 和 `eb create --single` 部署一个 `t3.micro`。
SSH 私钥只存于本人用户目录的 `.ssh`，不会写入仓库。

`.ebextensions/django.config` 包含 PDF 要求的 `DJANGO_SETTINGS_MODULE`、`PYTHONPATH`
和 `WSGIPath`，以及自动数据库迁移、示例题目和静态文件收集。
实际 EB 域名会加入 `DJANGO_ALLOWED_HOSTS`。服务器随机生成生产 secret，生产环境关闭 DEBUG。

同名环境存在且为 Ready 时，再运行脚本会部署代码更新。部署途中失败时先查看状态和日志，
不要连续创建多个环境。脚本不会自动把 AWS 账号升级为 Paid plan。
只有在账号登录后，才能实际验证云端 IAM、平台和启动行为；本地测试不能替代云端部署验证。

常用诊断命令（环境名通常为 `swe1-app-你的AWS账号ID`）：

```powershell
.\.ebcli-venv\Scripts\eb.exe status 环境名
.\.ebcli-venv\Scripts\eb.exe events 环境名
.\.ebcli-venv\Scripts\eb.exe logs 环境名
```

本次已在本机和 AWS 实例创建管理员 `course-admin`。本作业专用密码保存在本机
`%USERPROFILE%\.swe1-app\admin-login.env`，文件权限仅允许本人访问，位于 Git 仓库和部署包之外。

今后需要新建管理员时，用 SSH 登录实例，再创建本人密码：

```powershell
ssh -i "$env:USERPROFILE\.ssh\环境名-us-east-1.pem" ec2-user@实例公网地址
```

在服务器执行：

```bash
cd /var/app/current
source /var/app/venv/*/bin/activate
export DJANGO_SETTINGS_MODULE=mysite.settings
export DJANGO_DEBUG=False
export DJANGO_SECRET_KEY_FILE=/var/app/data/django-secret-key
export DJANGO_DATABASE_PATH=/var/app/data/db.sqlite3
sudo --preserve-env=DJANGO_SETTINGS_MODULE,DJANGO_DEBUG,DJANGO_SECRET_KEY_FILE,DJANGO_DATABASE_PATH -u webapp python manage.py createsuperuser
```

管理后台为应用域名下的 `/admin/`。管理员账号不需要提供给老师才能进行公开投票。
单实例默认端点为 HTTP；如果没有额外配置 TLS，不要将链接改成 HTTPS。
HTTP 环境只使用本作业专用管理员密码，不要复用其他网站密码。

## 5. 最终验证与提交

部署脚本只有在云端首页检查通过后，才会生成 `SUBMISSION.md` 中的真实应用 URL。
再用无痕窗口打开该 URL：

- 首页显示示例题目。
- 点开题目，选一个选项并提交，跳转结果页且票数增加。
- 不选选项直接提交，出现错误提示，票数不变。
- 回到首页、再次投票均可正常使用。
- GitHub 仓库可直接访问，默认分支包含代码及迁移文件。

GitHub 仓库地址：https://github.com/yh6415-lgtm/swe1-app
已部署的应用地址：http://swe1-app-287872994760.us-east-1.elasticbeanstalk.com/polls/
2026-10-11 已验证云端首页、无选项错误提示、投票和结果页；EB 状态为 Ready / Green。
在 Brightspace 提交两个真实链接，不要提交 localhost、示例域名或 AWS 控制台地址。

评分完成后在 EB 控制台终止本作业环境，并检查 EC2、EBS、Elastic IP、S3 等残留资源。
不要提前关闭环境，老师会手动访问链接评分。
