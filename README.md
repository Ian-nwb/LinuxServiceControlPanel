# Service Control Panel

A Tokyo Night–themed desktop GUI for managing local development services on Linux Mint (and any Ubuntu/Debian-based system). Built with Python + Tkinter — no Electron, no browser, no bloat.

---

## What it manages

| Service | Icon | What it is |
|---|---|---|
| MySQL | 🐬 | Relational database |
| PostgreSQL | 🐘 | Relational database |
| MongoDB | 🍃 | Document database |
| Redis | 🔴 | In-memory key-value store |
| Docker | 🐳 | Container runtime |
| Nginx | ⚡ | Web server / reverse proxy |

---

## Prerequisites

### 1. Python + Tkinter

Tkinter ships with Python on most systems, but Linux Mint sometimes strips it out. Verify:

```bash
python3 -c "import tkinter; print('ok')"
```

If that errors, install it:

```bash
sudo apt install python3-tk
```

### 2. pkexec (PolicyKit)

The panel uses `pkexec` to run `systemctl` commands with root privileges — it triggers a GUI password popup instead of requiring `sudo` in a terminal. It's pre-installed on Linux Mint. Verify:

```bash
which pkexec
```

### 3. journalctl

Used by the Logs window to pull service output. Comes with `systemd`, which is already on your system.

---

## Installation

Place both files in the same folder:

```
your-folder/
├── dbcontrol-gui.py
└── setup-dbcontrol-gui.sh
```

Then run the setup script:

```bash
chmod +x setup-dbcontrol-gui.sh
./setup-dbcontrol-gui.sh
```

The setup script will:

- Check for `python3-tk` and install it if missing
- Copy `dbcontrol-gui.py` to `~/.local/bin/`
- Create a `.desktop` entry so it appears in your app menu as **Service Control Panel**
- Register it with the desktop database

### Running manually (without installing)

```bash
python3 dbcontrol-gui.py
```

### Running after installation

Search **"Service Control Panel"** in your app menu, or run:

```bash
python3 ~/.local/bin/dbcontrol-gui.py
```

---

## UI overview

```
┌─────────────────────────────────────────────────────────────────┐
│  ⚙  Service Control Panel                       HH:MM:SS       │
├──────────────────────────────────────────────────────────────── │
│  · SERVICE    STATUS       UPTIME   BOOT      [▶][■][↺][📋]    │
│  ● MySQL      ● running    2h 14m   auto-start                  │
│  ○ PostgreSQL ○ stopped             manual                      │
│  ● MongoDB    ● running    45m      auto-start                  │
│  ○ Redis      ○ stopped             manual                      │
│  ● Docker     ● running    3h 02m   auto-start                  │
│  ○ Nginx      ○ stopped             manual                      │
├─────────────────────────────────────────────────────────────────│
│  3/6 services running • last refreshed 14:22:01   [↻ Refresh]  │
└─────────────────────────────────────────────────────────────────┘
```

### Columns

| Column | Description |
|---|---|
| Dot | Animated pulse (green = running, red = stopped, amber = working) |
| Service | Name and icon |
| Status | `● running` or `○ stopped` or `not installed` |
| Uptime | How long the service has been active (only shown when running) |
| Boot | `auto-start` = starts on boot; `manual` = stays off until you start it |

### Buttons

| Button | Action |
|---|---|
| ▶ start | `systemctl start <service>` |
| ■ stop | `systemctl stop <service>` |
| ↺ restart | `systemctl restart <service>` |
| 📋 logs | Opens a log window pulling from `journalctl` |

> All start/stop/restart actions trigger a **pkexec password popup** — this is expected. The panel never stores your password.

### Log window

Click **📋 logs** on any row to open a live log viewer for that service. Lines are color-coded:

- 🔴 Red — `error`, `failed`, `fatal`, `crit`
- 🟡 Amber — `warn`, `notice`
- 🟢 Green — `start`, `ready`, `success`, `listening`

Click **↻ refresh** inside the log window to pull the latest entries.

### Auto-refresh

The panel refreshes all service statuses every **8 seconds** automatically. Click **↻ Refresh All** in the footer to trigger it manually.

---

## Enable / disable autostart

The panel shows whether each service starts on boot, but toggling it requires a terminal command:

```bash
# make a service start on boot
sudo systemctl enable <service>

# prevent a service from starting on boot
sudo systemctl disable <service>

# check current state
systemctl is-enabled <service>
```

Example — disable Nginx autostart (good for local dev where you start it manually):

```bash
sudo systemctl disable nginx
```

---

## The services — what they are and when to use them

### 🐬 MySQL

A widely used **relational database** (SQL). Stores data in tables with rows and columns. Best for structured data with clear relationships — users, orders, products.

**Install:**
```bash
sudo apt install mysql-server
sudo mysql_secure_installation   # run after install to set root password
```

**When to use it:**
- PHP/Laravel backends (the traditional LAMP stack)
- Projects that need strict schema enforcement
- When your team or client already uses MySQL in production

**Key files:**
- Config: `/etc/mysql/mysql.conf.d/mysqld.cnf`
- Data: `/var/lib/mysql/`

**Common commands:**
```bash
mysql -u root -p              # open MySQL shell
SHOW DATABASES;
CREATE DATABASE myapp;
```

---

### 🐘 PostgreSQL

A more powerful **relational database** than MySQL — better support for complex queries, JSON columns, full-text search, and custom types. The preferred SQL database for most modern backend work.

**Install:**
```bash
sudo apt install postgresql postgresql-contrib
```

**When to use it:**
- Node.js/Express backends (pairs well with Prisma or Knex)
- Projects using TypeScript + Prisma (your DIETA setup uses this)
- When you need JSON columns, arrays, or advanced indexing
- Anything going to production on a serious stack

**Key files:**
- Config: `/etc/postgresql/<version>/main/postgresql.conf`
- Data: `/var/lib/postgresql/`

**Common commands:**
```bash
sudo -u postgres psql          # open psql shell
\l                             # list databases
CREATE DATABASE myapp;
\c myapp                       # connect to a database
```

---

### 🍃 MongoDB

A **document database** — stores data as JSON-like documents instead of rows and columns. Schema is flexible; each document can have different fields.

**Install:**
```bash
# Import the MongoDB GPG key and repo first
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
```

**When to use it:**
- Node.js/Express APIs (pairs naturally with Mongoose)
- Projects where the data shape changes often
- Your HR Attendance API and TRISHA backend use MongoDB Atlas — run a local instance during development to avoid hitting your cloud quota

**Key files:**
- Config: `/etc/mongod.conf`
- Data: `/var/lib/mongodb/`

**Common commands:**
```bash
mongosh                        # open MongoDB shell
show dbs
use myapp
db.users.find()
```

---

### 🔴 Redis

An **in-memory key-value store** — extremely fast because everything lives in RAM. Used as a cache, session store, message broker, or pub/sub system.

**Install:**
```bash
sudo apt install redis-server
```

**When to use it:**
- Caching expensive database queries (store the result in Redis for 60 seconds, skip the DB hit)
- Storing session tokens / JWT blocklists
- Rate limiting API endpoints (increment a counter per IP per minute)
- Background job queues (with BullMQ or similar)

**Key files:**
- Config: `/etc/redis/redis.conf`

**Common commands:**
```bash
redis-cli                      # open Redis shell
SET mykey "hello"
GET mykey
TTL mykey                      # check time-to-live
KEYS *                         # list all keys (avoid on production)
```

---

### 🐳 Docker

A **container runtime** — packages an app and all its dependencies into an isolated container that runs the same everywhere. No more "it works on my machine."

**Install:**
```bash
# Official Docker install (recommended over apt version)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # run Docker without sudo (re-login after)
```

**When to use it:**
- Running a database without installing it natively (e.g. `docker run -d -p 5432:5432 postgres`)
- Keeping projects isolated from your host system
- Deploying apps — build an image once, run anywhere
- Running third-party tools (Adminer, pgAdmin, Mailhog) without polluting your system

**Key commands:**
```bash
docker ps                            # list running containers
docker images                        # list local images
docker run -d -p 3306:3306 mysql     # run MySQL in a container
docker compose up -d                 # start all services from docker-compose.yml
docker compose down                  # stop and remove containers
docker logs <container>              # view container output
```

**docker-compose.yml example** for a Node + MongoDB + Redis stack:
```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - mongo
      - redis

  mongo:
    image: mongo:7
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  mongo_data:
```

---

### ⚡ Nginx

A high-performance **web server and reverse proxy**. In local dev and production, it sits in front of your apps and routes traffic to them.

**Install:**
```bash
sudo apt install nginx
```

**When to use it:**

**Reverse proxy** — expose your Node app on port 80 instead of 3000:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**Serve a React/Vite build** — static files, no Node needed:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    root /var/www/myapp/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;  # required for React Router
    }
}
```

**Multiple projects on one machine:**
```nginx
server { server_name api.yourdomain.com;  location / { proxy_pass http://localhost:3000; } }
server { server_name app.yourdomain.com;  root /var/www/frontend/dist; location / { try_files $uri /index.html; } }
```

**SSL with Let's Encrypt (free):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

**Key commands:**
```bash
sudo nginx -t                  # test config for syntax errors
sudo systemctl reload nginx    # apply config changes without downtime
sudo nginx -s reload           # alternative reload
```

**Key paths:**
| Path | Purpose |
|---|---|
| `/etc/nginx/nginx.conf` | Main config |
| `/etc/nginx/sites-available/` | Write your site configs here |
| `/etc/nginx/sites-enabled/` | Symlink active configs here |
| `/var/log/nginx/access.log` | All incoming requests |
| `/var/log/nginx/error.log` | Errors and warnings |

**Activate a site config:**
```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## Recommended local dev setup

For a typical Node.js full-stack project, you generally only need a few services running at once:

| Stack | Services to run |
|---|---|
| Node + MongoDB (e.g. TRISHA backend) | MongoDB, Redis (optional for sessions), Nginx (if testing proxy) |
| Node + PostgreSQL (e.g. DIETA) | PostgreSQL, Redis (optional), Nginx (optional) |
| Fully containerized project | Docker only — everything else runs inside containers |
| Frontend only (Vite dev server) | Nothing — Vite handles its own dev server |

> **Tip:** Keep autostart disabled for everything you don't use daily. Start only what the current project needs. This keeps your machine fast and avoids port conflicts between projects.

---

## Troubleshooting

### "not installed" shown for a service

The service binary isn't on your system yet. Install it using the commands in the relevant section above, then click **↻ Refresh All**.

### pkexec popup doesn't appear

On some setups `pkexec` requires a running polkit agent. If the popup never shows:

```bash
# Check if polkit is running
systemctl status polkit

# Start it if needed
sudo systemctl start polkit
```

### Port already in use

If a service fails to start, another process may be on its port:

```bash
sudo ss -tulpn | grep <port>   # e.g. grep 3306 for MySQL
```

Kill the process or stop the conflicting service first.

### Log window shows no output

Some services write to their own log files instead of journald. Check:

```bash
# MySQL
sudo tail -f /var/log/mysql/error.log

# Nginx
sudo tail -f /var/log/nginx/error.log

# MongoDB
sudo tail -f /var/log/mongodb/mongod.log
```# LinuxServiceControlPanel
