# TechCorp Product Documentation

## GETTING STARTED

### Account Signup and Email Verification
1. Visit app.techcorp.io and click "Sign Up"
2. Enter your work email address and create a password
3. Check your inbox for a verification email (may take 2-3 minutes)
4. Click the verification link to activate your account
5. If you don't receive the email, check your spam folder or click "Resend Verification"

### Onboarding Wizard
After email verification, you'll be guided through:
1. **Create Workspace**: Enter your company name and choose a workspace URL
2. **Invite Team**: Add team members by email (skip if you want to do this later)
3. **Create First Project**: Choose a template or start from scratch
4. **Set Up Integrations**: Connect Slack, Google Drive, or other tools

### Dashboard Overview
- **Left Sidebar**: Navigation menu (Projects, Tasks, Team, Reports, Settings)
- **Main Area**: Your projects and recent activity
- **Top Bar**: Search, notifications, and user profile
- **Quick Actions**: "+ New" button for projects, tasks, or invitations

## USER MANAGEMENT

### Inviting Members
1. Go to **Settings → Team**
2. Click "Invite Members"
3. Enter email addresses (comma-separated)
4. Select role for each member
5. Click "Send Invitations"
6. Members will receive email invites valid for 7 days

### User Roles
- **Admin**: Full access to all features, billing management, user management
- **Member**: Can create/edit tasks, view projects, collaborate on assigned work
- **Viewer**: Read-only access to view projects and tasks (no editing permissions)

### Removing Users
1. Go to **Settings → Team**
2. Find the user and click the three-dot menu
3. Select "Remove from Workspace"
4. Choose whether to reassign their tasks to someone else
5. Confirm removal

### Transferring Workspace Ownership
1. Current owner goes to **Settings → Workspace**
2. Click "Transfer Ownership"
3. Select the new owner (must be an Admin)
4. Enter your password to confirm
5. New owner will receive email confirmation

### SSO Setup (Enterprise Plan Only)
1. Contact sales@techcorp.io to request SSO setup
2. Provide your SAML provider details
3. Our team will configure SSO integration
4. Test SSO login with your IT administrator
5. Roll out to your team members

## TASK AND PROJECT MANAGEMENT

### Creating a Project
1. Click "+ New Project" in the sidebar
2. Enter project name and description
3. Choose view type:
   - **Kanban**: Visual board with drag-and-drop cards
   - **List**: Traditional task list with details
   - **Timeline**: Gantt chart view with dependencies
4. Set project start/end dates (optional)
5. Add team members
6. Click "Create Project"

### Creating Tasks
1. Open your project
2. Click "+ Add Task" or press "T"
3. Fill in task details:
   - **Title**: Clear, actionable description
   - **Description**: Detailed instructions or requirements
   - **Assignee**: Choose from team members
   - **Due Date**: Click calendar to set deadline
   - **Priority**: Low, Medium, High, or Critical
4. Click "Create Task"

### Subtasks
1. Open any task to view details
2. Click "+ Add Subtask" below the main task
3. Enter subtask title and assign if needed
4. Subtasks inherit due date from parent task (can be changed)
5. Mark subtasks complete independently

### Task Dependencies
1. Right-click on any task
2. Select "Set Dependency"
3. Choose the task that must be completed first
4. Choose dependency type:
   - **Finish to Start**: Task B starts when Task A finishes
   - **Start to Start**: Task B starts when Task A starts
5. Dependent tasks will be automatically blocked until prerequisite is complete

### Tags and Labels
1. Click on any task to open details
2. Click "Labels" section
3. Select existing labels or click "+ New Label"
4. Choose color and name for new label
5. Labels help with filtering and organization

### Recurring Tasks
1. Open task settings (gear icon)
2. Click "Recurrence"
3. Set frequency:
   - Daily, Weekly, Monthly, or Custom
   - Choose days of week for weekly recurrence
   - Set end date or number of occurrences
4. Save settings
5. New instances will be created automatically

## FILES AND STORAGE

### Uploading Files to Tasks
1. Open the task where you want to add files
2. Click "Attachments" section
3. Drag and drop files or click "Upload Files"
4. Wait for upload completion (progress bar shown)
5. Files are automatically versioned

### File Size and Format Limits
- **Maximum file size**: 100MB per file
- **Supported formats**: All common file types including:
  - Documents: PDF, DOC, DOCX, TXT, RTF
  - Spreadsheets: XLS, XLSX, CSV
  - Images: JPG, PNG, GIF, SVG, WebP
  - Presentations: PPT, PPTX, KEY
  - Archives: ZIP, RAR, 7Z
  - Code files: All programming language files

### Storage Limits by Plan
- **Starter**: 10GB total storage
- **Pro**: 100GB total storage
- **Enterprise**: Unlimited storage
- Storage usage shown in **Settings → Billing**

### File Sharing
- Files shared with all project members by default
- Can set file-level permissions for sensitive documents
- External sharing generates secure links with expiration dates

## INTEGRATIONS

### Slack Integration
1. Go to **Settings → Integrations → Slack**
2. Click "Connect to Slack"
3. Authorize TechCorp in your Slack workspace
4. Choose channels for notifications:
   - Task assignments
   - Project updates
   - Deadline reminders
5. Customize notification preferences
6. Test integration with sample notification

### Google Drive Integration
1. Navigate to **Settings → Integrations → Google Drive**
2. Click "Connect Google Drive"
3. Sign in with your Google account
4. Grant necessary permissions
5. Once connected:
   - Browse Drive files directly in TechCorp
   - Attach Drive files to tasks without uploading
   - Sync file permissions automatically

### GitHub Integration
1. Go to **Settings → Integrations → GitHub**
2. Click "Connect GitHub Repository"
3. Authorize with your GitHub account
4. Select repositories to connect
5. Link commits to tasks by including task ID in commit messages
   - Example: "Fix login issue [T123]"
6. View commit history and code changes within tasks

### Zapier Integration
1. Search "TechCorp" in Zapier's app directory
2. Choose from 500+ pre-built automation templates
3. Popular automations include:
   - Create tasks from new emails
   - Sync with calendar events
   - Post updates to social media
   - Generate reports automatically
4. Follow Zapier's setup wizard for each automation

## API ACCESS

### API Availability
- REST API available on Pro and Enterprise plans only
- Full CRUD operations for projects, tasks, and users
- Real-time webhooks for event notifications

### Rate Limits
- **Pro Plan**: 1,000 requests per hour
- **Enterprise Plan**: 5,000 requests per hour
- Rate limit headers included in all API responses

### API Key Generation
1. Go to **Settings → API**
2. Click "Generate New Key"
3. Give your key a descriptive name
4. Copy the key immediately (shown only once)
5. Store securely in your application

### Webhooks Configuration
1. Navigate to **Settings → API → Webhooks**
2. Click "Add Webhook"
3. Enter your endpoint URL
4. Select events to subscribe to:
   - Task created/updated/deleted
   - Project changes
   - User activities
5. Test webhook with sample payload

### API Documentation
Complete API documentation available at: developers.techcorp.io
- Authentication methods
- Endpoint reference
- Code examples in multiple languages
- SDK downloads

## BILLING AND PAYMENTS

### Payment Methods
- **Credit Card**: Visa, MasterCard, American Express (all plans)
- **Bank Transfer**: Available for Enterprise plans only
- **ACH**: US customers on Enterprise plans

### Billing Cycles
- **Monthly**: Billed on the same day each month
- **Annual**: Pay for 12 months, get 2 months free
- Annual plans save ~17% compared to monthly billing

### Plan Changes
- **Upgrades**: Take effect immediately, prorated charges apply
- **Downgrades**: Take effect at the end of current billing cycle
- No refunds for partial months on downgrades

### Invoices and Receipts
- Invoices emailed automatically on each billing date
- PDF copies available in **Settings → Billing → Invoice History**
- Receipts include tax information and payment details

### Billing Disputes
- All billing disputes handled by our billing team
- Contact billing@techcorp.io for payment issues
- Include invoice number and detailed explanation
- Support agents cannot process refunds or billing adjustments

## PASSWORD RESET

### Standard Password Reset
1. Click "Forgot Password" on the login page
2. Enter your registered email address
3. Check your inbox (and spam folder) for reset email
4. Click the reset link (expires in 24 hours)
5. Create a new password meeting security requirements:
   - Minimum 12 characters
   - Include uppercase, lowercase, numbers, and symbols
6. Confirm new password and log in

### Troubleshooting Password Reset
- **No email received**: Check spam folder, verify email address, wait 5 minutes
- **Link expired**: Request a new reset email
- **Multiple attempts**: Account locked for 30 minutes after 5 failed attempts

### SSO Account Passwords
- For SSO accounts, contact your IT administrator
- Password reset handled through your company's identity provider
- TechCorp support cannot reset SSO passwords

## TWO-FACTOR AUTHENTICATION (2FA)

### Enabling 2FA
1. Go to **Settings → Security → Two-Factor Authentication**
2. Click "Enable 2FA"
3. Scan the QR code with your authenticator app:
   - Google Authenticator
   - Authy
   - Microsoft Authenticator
4. Enter the 6-digit code to verify setup
5. Save your backup codes in a secure location

### Backup Codes
- 10 backup codes provided during setup
- Each code can be used once
- Store codes securely (password manager, safe deposit box)
- Generate new backup codes if old ones are compromised

### Disabling 2FA
1. Go to **Settings → Security → 2FA**
2. Click "Disable 2FA"
3. Enter your current 2FA code
4. Confirm password
5. 2FA will be immediately disabled

## MOBILE APPLICATIONS

### Availability
- **iOS**: App Store, iOS 14.0 or later
- **Android**: Google Play Store, Android 8.0 or later
- Search for "TechCorp PM" in your app store

### Mobile Features
- Full task management capabilities
- Offline mode with automatic sync
- Push notifications for assignments
- File attachments and comments
- Project dashboards and reports

### Offline Mode
- Works without internet connection
- Changes saved locally and synced when reconnected
- Conflict resolution for simultaneous edits
- Downloaded projects available offline

### Mobile Login
- Use same credentials as web version
- SSO login supported on mobile
- Biometric authentication available (Face ID, fingerprint)

## TROUBLESHOOTING

### Login Issues
1. **Clear browser cache and cookies**
2. **Try incognito/private browsing mode**
3. **Check email verification status**
4. **Reset password if needed**
5. **Verify correct workspace URL**
6. **Contact support if issues persist**

### Performance Issues
- **Slow loading**: Check status.techcorp.io for system incidents
- **Hard refresh**: Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- **Browser compatibility**: Use Chrome, Firefox, Safari, or Edge (latest versions)
- **Internet connection**: Minimum 5 Mbps recommended

### Sync Issues
1. Go to **Settings → Sync**
2. Click "Force Refresh"
3. Wait 2-3 minutes for full sync
4. Check internet connection stability
5. Restart browser if needed

### Permission Issues
- **Can't see project**: Ask workspace Admin to verify your role
- **Can't edit tasks**: Ensure you have Member or Admin role
- **Missing features**: Some features limited by subscription plan

### Integration Problems
1. **Disconnect the problematic integration**
2. **Clear browser cache**
3. **Reconnect the integration**
4. **Reauthorize with fresh credentials**
5. **Test with sample data**

### Mobile App Issues
1. **Log out and log back in**
2. **Force close and restart the app**
3. **Check for app updates**
4. **Wait 2 minutes for sync to complete**
5. **Reinstall app if problems persist**

### Common Error Messages
- **"Workspace not found"**: Check URL spelling, verify you're member of workspace
- **"Invalid credentials"**: Reset password or check for typos
- **"Rate limit exceeded"**: Wait 15 minutes before trying again
- **"File too large"**: Compress file or use cloud storage link
- **"Integration failed"**: Reauthorize the third-party service

## CONTACTING SUPPORT

### Support Channels
- **Email**: support@techcorp.io
- **In-app chat**: Available in Pro and Enterprise plans
- **Phone**: Enterprise customers only
- **Knowledge base**: help.techcorp.io

### Support Hours
- **Standard Support**: Monday-Friday, 9 AM-6 PM EST
- **Priority Support**: Pro plan, 24/7 for critical issues
- **Enterprise Support**: 24/7 dedicated support team

### Response Times
- **Critical issues**: Under 1 hour
- **High priority**: Under 4 hours
- **Standard questions**: Under 24 hours
- **Low priority**: Under 48 hours
