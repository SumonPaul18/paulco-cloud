# ☁️ Paulco Cloud - Custom OpenStack Dashboard using Flask

Paulco Cloud is a custom-built Python Flask web application designed to provide a simple, secure, and user-friendly dashboard interface for managing OpenStack Cloud resources.

This project integrates Google OAuth 2.0 authentication and email notifications, making it ideal for both personal and enterprise cloud automation needs.

---

## 📌 Features

- 🔐 Google OAuth 2.0 Authentication
- ☁️ OpenStack API Integration (via `clouds.yaml`)
- 📧 Email Notifications (Gmail SMTP)
- 📊 Web Dashboard using Flask + Bootstrap
- 🐳 Docker & Docker Compose Support

---

## 📁 Project Structure

```

├── app.py                  # Entry point of the Flask application
├── main.py                 # Main application logic
├── dashboard.py            # UI route handling and dashboard logic
├── openstack\_component.py  # OpenStack component API functions
├── clouds.yaml             # OpenStack environment configuration
├── .env                    # Environment variables (Google OAuth, Mail, Secrets)
├── requirements.txt        # Python dependencies
├── docker-compose.yml      # Docker Compose setup
├── Dockerfile              # Docker image build config
├── templates/              # Jinja2 HTML templates
├── static/                 # Static assets (CSS, JS)
└── readme.md               # Project documentation

````

---

## 🔐 Required `.env` Configuration

Create a `.env` file in the project root with the following content (modify according to your environment):

```env
SECRET_KEY=paulco.xyz

# Google OAuth Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
OAUTHLIB_RELAX_TOKEN_SCOPE=1
OAUTHLIB_INSECURE_TRANSPORT=1

# Mail Server Configuration
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_app_specific_password
MAIL_USE_TLS=True
MAIL_USE_SSL=False
````

> ⚠️ Do not expose your real credentials in public repositories. Always use `.gitignore` to prevent committing the `.env` file.

---

## 🛠️ Installation & Usage

### 🧰 Prerequisites

* Docker & Docker Compose installed
* A valid OpenStack environment with `clouds.yaml` configured
* Google Cloud project with OAuth credentials

### 🚀 Running the Application (Docker)

```bash
# Clone the repository
git clone https://github.com/SumonPaul18/paulco-cloud.git
cd paulco-cloud

# Create your .env file as shown above
cp .env.example .env  # (if you create a template)

# Run with Docker Compose
docker-compose up --build
```

### 🧪 Run Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (manually or via .env)
# Run the application
python app.py
```

---

## 🔄 Future Improvements

* 🌐 Multi-User Role-Based Access Control (RBAC)
* 📦 Integration with Ceilometer or Gnocchi for resource monitoring
* 📊 Usage-based billing dashboard
* 💬 Admin dashboard with log viewer and analytics
* 🌍 Internationalization (i18n) and localization support
* ☁️ Support for other clouds (AWS, Azure, GCP)

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙌 Acknowledgements

* [Flask](https://flask.palletsprojects.com/)
* [OpenStack SDK](https://docs.openstack.org/openstacksdk/)
* [Google OAuth 2.0](https://developers.google.com/identity/protocols/oauth2)
* [Docker](https://www.docker.com/)

```
---
