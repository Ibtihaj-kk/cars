# 📧 Email Service Operations Guide

## 🚀 Overview
This guide covers the setup, configuration, and operation of your centralized email service system.

## 📋 System Architecture

### Core Components
- **EmailOrchestrator**: Central coordinator for all email operations
- **Email Providers**: SMTP, SendGrid, Mailgun implementations
- **Email Queue**: Database-backed queue with status tracking
- **Handlers**: Specialized processors for different email types
- **Admin Console**: Web interface for manual operations

### Email Types Supported
- `verification` - User email verification
- `vendor_approval` - Vendor application approved
- `vendor_rejection` - Vendor application rejected
- `manual_admin` - Manual emails from admin console
- `bulk_admin` - Bulk emails to user groups

## ⚙️ Configuration

### 1. Environment Variables
Add these to your `.env` file:

```bash
# Email Service Configuration
EMAIL_SERVICE_ENABLED=true
EMAIL_PROVIDER=smtp  # smtp, sendgrid, or mailgun
EMAIL_QUEUE_PROCESSING_INTERVAL=300  # 5 minutes
EMAIL_MAX_RETRIES=3
EMAIL_RETRY_DELAY=300  # 5 minutes

# SMTP Configuration (if using SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false

# SendGrid Configuration (if using SendGrid)
SENDGRID_API_KEY=your-sendgrid-api-key
SENDGRID_SANDBOX_MODE=false

# Mailgun Configuration (if using Mailgun)
MAILGUN_API_KEY=your-mailgun-api-key
MAILGUN_DOMAIN=your-domain.com
```

### 2. Django Settings
Add to `settings.py`:

```python
# Email Service Configuration
EMAIL_SERVICE_CONFIG = {
    'ENABLED': env.bool('EMAIL_SERVICE_ENABLED', True),
    'PROVIDER': env('EMAIL_PROVIDER', 'smtp'),
    'QUEUE_PROCESSING_INTERVAL': env.int('EMAIL_QUEUE_PROCESSING_INTERVAL', 300),
    'MAX_RETRIES': env.int('EMAIL_MAX_RETRIES', 3),
    'RETRY_DELAY': env.int('EMAIL_RETRY_DELAY', 300),
    'BATCH_SIZE': env.int('EMAIL_BATCH_SIZE', 50),
}

# Fallback to Django's email settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', 587)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', True)
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', 'noreply@yourdomain.com')
```

## 🛠️ Setup Instructions

### 1. Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Create Superuser (for admin access)
```bash
python manage.py createsuperuser
```

### 3. DNS Configuration for Email Deliverability

#### Essential DNS Records for Email Authentication

**SPF (Sender Policy Framework)** - Prevents email spoofing
```dns
# TXT record for SPF
v=spf1 include:_spf.carsyncro.com include:spf.protection.outlook.com include:amazonses.com ~all

# Or for simple setup:
v=spf1 a mx include:_spf.google.com ~all
```

**DKIM (DomainKeys Identified Mail)** - Email authentication and integrity
```dns
# DKIM record (provider-specific)
# For SendGrid: s1._domainkey.yourdomain.com
# For Mailgun: k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC4...

# Example DKIM record
domainkey._domainkey IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQD..."
```

**DMARC (Domain-based Message Authentication, Reporting & Conformance)**
```dns
# DMARC policy record
_dmarc IN TXT "v=DMARC1; p=none; rua=mailto:dmarc-reports@carsyncro.com; ruf=mailto:dmarc-forensics@carsyncro.com;"

# For stricter policy (after testing):
_dmarc IN TXT "v=DMARC1; p=quarantine; pct=100; rua=mailto:dmarc-reports@carsyncro.com;"
```

**MX Records** (if hosting your own email)
```dns
# MX records for incoming email
@ IN MX 10 mail.carsyncro.com.
@ IN MX 20 backup.carsyncro.com.
```

**Reverse DNS (PTR Record)** - Required for some providers
```dns
# PTR record for your mail server IP
# Contact your hosting provider to set this up
```

#### Domain Verification Records

**For SendGrid Domain Authentication**
```dns
# TXT record for domain verification
carsyncro-com-123456 IN TXT "sendgrid-domain-verification=abc123"

# CNAME records for link branding
em1234.carsyncro.com IN CNAME sendgrid.net.
url1234.carsyncro.com IN CNAME sendgrid.net.
```

**For Mailgun Domain Verification**
```dns
# TXT record for domain verification
mailgun._domainkey.carsyncro.com IN TXT "k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC4..."

# For tracking domain
email.carsyncro.com IN CNAME mailgun.org.
```

### 4. Configure Email Providers

#### Option A: SMTP (Gmail/Outlook)
1. Enable 2-factor authentication on your email account
2. Generate an app-specific password
3. Update environment variables with your credentials

#### Option B: SendGrid
1. Create SendGrid account at sendgrid.com
2. Generate API key with "Mail Send" permissions
3. Set `EMAIL_PROVIDER=sendgrid` and add API key

#### Option C: Mailgun
1. Create Mailgun account at mailgun.com
2. Verify your domain
3. Set `EMAIL_PROVIDER=mailgun` and add API key/domain

### 5. DNS Verification and Testing

#### DNS Verification Tools
```bash
# Check DNS records
dig carsyncro.com TXT
dig _dmarc.carsyncro.com TXT
dig default._domainkey.carsyncro.com TXT

# Check MX records
dig carsyncro.com MX

# Check reverse DNS
dig -x YOUR_SERVER_IP

# Online verification tools:
# - MXToolbox.com
# - DNSchecker.org
# - Google Admin Toolbox
```

#### Email Deliverability Testing
```bash
# Test email configuration
python manage.py test_email_configuration

# Send test email with full headers
python manage.py send_test_email --full-headers

# Check blacklist status
python manage.py check_blacklist_status
```

#### Best Practices for Email Deliverability

1. **Warm Up Your IP Address**
   - Start with small volumes (50-100 emails/day)
   - Gradually increase volume over 2-4 weeks
   - Monitor reputation scores

2. **Maintain Good Sender Reputation**
   - Keep bounce rate below 2%
   - Maintain spam complaint rate below 0.1%
   - Remove invalid emails promptly

3. **Content Best Practices**
   - Avoid spam trigger words
   - Balance text-to-image ratio
   - Include unsubscribe link
   - Use proper HTML structure

4. **Monitoring and Maintenance**
   - Regularly check blacklists
   - Monitor bounce and complaint rates
   - Update DNS records as needed
   - Renew SSL certificates

#### Common DNS Issues and Solutions

**SPF Too Many DNS Lookups**
```dns
# Problem: SPF record exceeds 10 DNS lookup limit
# Solution: Consolidate includes or use SPF macros
v=spf1 include:spf.protection.outlook.com include:amazonses.com ~all
```

**DKIM Key Too Long**
```dns
# Problem: DKIM key exceeds 255 character limit per string
# Solution: Use multiple TXT records or shorter key
"v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQC4"
"...continued key data..."
```

**DMARC Policy Too Strict**
```dns
# Start with monitoring mode
_dmarc IN TXT "v=DMARC1; p=none; rua=mailto:reports@carsyncro.com;"

# Gradually move to enforcement after monitoring
_dmarc IN TXT "v=DMARC1; p=quarantine; pct=25; rua=mailto:reports@carsyncro.com;"
```

## 🔄 Operation Commands

### 1. Start Email Processing
```bash
# Process emails in foreground
python manage.py process_email_queue

# Process as daemon (recommended for production)
python manage.py process_email_queue --daemon

# Process with specific batch size
python manage.py process_email_queue --batch-size 100

# Process only high priority emails
python manage.py process_email_queue --priority high
```

### 2. Check Verification Expiry
```bash
# Check and block unverified accounts (run daily)
python manage.py check_verification_expiry

# Dry run (no changes)
python manage.py check_verification_expiry --dry-run

# Specific verification period
python manage.py check_verification_expiry --days 3
```

### 3. Monitor Email Queue
```bash
# View queue status
python manage.py email_queue_status

# Retry failed emails
python manage.py retry_failed_emails

# Clear old emails from queue
python manage.py clear_email_queue --days 30
```

## 📊 Admin Console Usage

### Access Points
- **Email Console**: `/admin/email-console/`
- **Email Queue**: `/admin/email-queue/`
- **Email Analytics**: `/admin/email-analytics/`

### Manual Email Operations

#### 1. Send Single Email
1. Go to Email Console → Manual Send
2. Enter recipient email(s) (comma-separated for multiple)
3. Select template or enter custom subject/message
4. Choose priority (High/Medium/Low)
5. Click "Send Email"

#### 2. Send Bulk Email
1. Go to Email Console → Bulk Send
2. Select user group (All Users, Vendors, Admins, etc.)
3. Choose template or enter custom content
4. Set scheduling options
5. Click "Send Bulk Email"

#### 3. Manage Email Queue
1. Go to Email Queue page
2. View emails by status (Queued, Processing, Sent, Failed)
3. Use filters to find specific emails
4. Retry failed emails individually or in bulk
5. Cancel pending emails if needed

## 🚨 Troubleshooting

### Common Issues

#### 1. DNS-Related Email Issues

**SPF Validation Failures**
```bash
# Check SPF record
dig carsyncro.com TXT +short

# Test SPF configuration
python manage.py test_spf_configuration

# Common SPF issues:
# - Missing SPF record
# - Incorrect IP addresses in SPF
# - Too many DNS lookups (>10)
```

**DKIM Signature Failures**
```bash
# Check DKIM record
dig default._domainkey.carsyncro.com TXT +short

# Test DKIM configuration
python manage.py test_dkim_configuration

# Common DKIM issues:
# - Missing or incorrect DKIM record
# - Key rotation without updating DNS
# - Selector mismatch between DNS and code
```

**DMARC Policy Rejections**
```bash
# Check DMARC record
dig _dmarc.carsyncro.com TXT +short

# Analyze DMARC reports
python manage.py analyze_dmarc_reports

# Common DMARC issues:
# - Policy too strict (p=reject) without proper setup
# - Missing aggregate/forensic reporting
# - Alignment failures between From domain and DKIM/SPF
```

**Reverse DNS Mismatch**
```bash
# Check reverse DNS
dig -x YOUR_SERVER_IP +short

# Common rDNS issues:
# - PTR record doesn't match forward DNS
# - No PTR record for mail server IP
# - Generic PTR record (like pool-xx-xx-xx-xx.isp.com)
```

#### 2. Emails Not Sending
```bash
# Check queue status
python manage.py email_queue_status

# Check provider configuration
python manage.py test_email_provider

# View detailed logs
tail -f logs/email_service.log
```

#### 2. SMTP Authentication Errors
1. Verify email credentials
2. Check if app password is generated (for Gmail)
3. Ensure less secure apps is enabled (if required)

#### 3. Rate Limiting
- Reduce batch size: `--batch-size 20`
- Increase processing interval: `EMAIL_QUEUE_PROCESSING_INTERVAL=600`
- Use multiple queues for different priorities

### Log Files
- `logs/email_service.log` - General email operations
- `logs/email_provider.log` - Provider-specific issues
- `logs/email_queue.log` - Queue processing details

## 📈 Monitoring & Analytics

### Key Metrics to Monitor
- **Queue Size**: Number of pending emails
- **Processing Rate**: Emails processed per minute
- **Success Rate**: Percentage of successful deliveries
- **Failure Reasons**: Common failure types
- **Delivery Time**: Average time from queue to delivery

### Dashboard Access
- Real-time metrics at `/admin/email-analytics/`
- Daily/weekly/monthly reports
- Provider performance statistics

## 🔒 Security Considerations

### 1. API Key Protection
- Never commit API keys to version control
- Use environment variables for all secrets
- Rotate keys regularly

### 2. Access Control
- Admin console requires staff/superuser privileges
- Audit all manual email operations
- Log all email sending activities

### 3. Data Protection
- Email content is stored encrypted in database
- Personal data is handled according to GDPR
- Regular security audits recommended

## 🚀 Production Deployment

### 1. Systemd Service (Linux)
Create `/etc/systemd/system/email-service.service`:
```ini
[Unit]
Description=Email Queue Processing Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/your/app
ExecStart=/usr/bin/python3 manage.py process_email_queue --daemon
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Cron Jobs
Add to crontab (`crontab -e`):
```bash
# Process email queue every 5 minutes
*/5 * * * * cd /path/to/your/app && python manage.py process_email_queue --batch-size 50

# Check verification expiry daily at 2 AM
0 2 * * * cd /path/to/your/app && python manage.py check_verification_expiry

# Clean old emails weekly
0 3 * * 0 cd /path/to/your/app && python manage.py clear_email_queue --days 30
```

### 3. Load Balancing
For high volume:
- Run multiple queue processors
- Use `--queue-name` parameter for separate queues
- Distribute by email type or priority

## 📞 Support

### Getting Help
1. Check logs in `logs/email_service.log`
2. Run diagnostic: `python manage.py email_service_diagnostic`
3. Review this operations guide

### Emergency Procedures
- **Service Down**: Restart processor service
- **Queue Backup**: Increase batch size temporarily
- **Provider Issues**: Switch to fallback provider

---

**Last Updated**: 2026-01-05
**Version**: 1.0.0
**System**: Centralized Email Service