# Service Control Panel

A Tokyo Night–themed desktop GUI for managing local development services on Linux Mint (and any Ubuntu/Debian-based system). Built with Python + Tkinter — no Electron, no browser, no bloat.

---

## What it manages

| Service | Icon | What it is | Default port |
|---|---|---|---|
| MySQL | 🐬 | Relational database | 3306 |
| PostgreSQL | 🐘 | Relational database | 5432 |
| MongoDB | 🍃 | Document database | 27017 |
| Redis | 🔴 | In-memory key-value store | 6379 |
| Docker | 🐳 | Container runtime | — |
| Nginx | ⚡ | Web server / reverse proxy | 80 |
| FileZilla | 📂 | FTP/SFTP client (launcher) | — |

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

The panel uses `pkexec` to run `systemctl` commands with root privileges — it triggers a GUI password popup instead of requiring `sudo` in a terminal. Pre-installed on Linux Mint. Verify:

```bash
which pkexec
```

### 3. journalctl

Used by the Logs window to pull service output. Comes with `systemd`, which is already on your system.

### 4. FileZilla (optional)

Only needed if you want the FileZilla launcher row to work:

```bash
sudo apt install filezilla
```

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
┌──────────────────────────────────────────────────────────────────────────────────┐
│  ⚙  Service Control Panel                                    Friday 26 Jun 14:22 │
├──────────────────────────────────────────────────────────────────────────────────┤
│  · SERVICE      STATUS      PORT       UPTIME  CPU    RAM    BOOT                │
│  ● MySQL        ● running   :3306 ●    2h14m   1.2s   48.3M  ☑ auto  ▶ ■ ↺ 📋  │
│  ○ PostgreSQL   ○ stopped   :5432 ○            —      —      ☐ auto  ▶ ■ ↺ 📋  │
│  ● MongoDB      ● running   :27017 ●   45m     0.4s   91.0M  ☑ auto  ▶ ■ ↺ 📋  │
│  ○ Redis        ○ stopped   :6379 ○            —      —      ☐ auto  ▶ ■ ↺ 📋  │
│  ● Docker       ● running              3h02m   2.1s   112M   ☑ auto  ▶ ■ ↺ 📋  │
│  ○ Nginx        ○ stopped   :80 ○              —      —      ☐ auto  ▶ ■ ↺ 📋  │
│  ─────────────────────────────────────────────────────────────────────────────── │
│  📂 FileZilla   launcher                                      📂 open FileZilla  │
├──────────────────────────────────────────────────────────────────────────────────┤
│  3/6 services running  •  last refreshed 14:22:01                  ↻ Refresh All │
└──────────────────────────────────────────────────────────────────────────────────┘
```

### Columns

| Column | Description |
|---|---|
| Dot | Animated pulse — green (running), red (stopped), amber (working) |
| Service | Name and icon |
| Status | `● running` or `○ stopped` or `not installed` |
| Port | Whether the service's default port is actually bound — catches crash-on-start |
| Uptime | How long the service has been active (running only) |
| CPU | Cumulative CPU time from `systemctl show` (purple) |
| RAM | Current memory usage from cgroups (cyan) |
| Boot | Checkbox — tick to enable autostart, untick to disable. Triggers pkexec. |

### Buttons

| Button | Action |
|---|---|
| ▶ start | `systemctl start <service>` |
| ■ stop | `systemctl stop <service>` |
| ↺ restart | `systemctl restart <service>` |
| 📋 logs | Opens a log window pulling from `journalctl` |
| 📂 open FileZilla | Launches FileZilla as a regular app (no pkexec needed) |

> Start/Stop/Restart and the Boot checkbox all trigger a **pkexec password popup** — this is expected. The panel never stores your password.

### Port indicator

The port column does a real TCP connection check (not just a systemd state check). This catches the case where a service reports `active` but immediately crashed — the port will show `○` even if systemd thinks it's running.

| Indicator | Meaning |
|---|---|
| `:3306 ●` (green) | Port is bound and accepting connections |
| `:3306 ○` (red) | Port is not bound — service may have crashed |
| `:80 ○` (muted) | Service is stopped, port is free (expected) |

### Boot checkbox

Ticking or unticking the **auto** checkbox runs `systemctl enable` or `systemctl disable` via pkexec. The checkbox re-reads the actual enabled state after the operation, so you always see what systemd actually recorded.

### Log window

Click **📋 logs** on any row to open a live log viewer for that service, pulling the last 60 lines from `journalctl`. Color-coded:

- 🔴 Red — `error`, `failed`, `fatal`, `crit`
- 🟡 Amber — `warn`, `notice`
- 🟢 Green — `start`, `ready`, `success`, `listening`

Click **↻ refresh** to pull the latest entries.

### Auto-refresh

All rows refresh automatically every **8 seconds**. Click **↻ Refresh All** in the footer to trigger immediately.

---

## The services — what they are and when to use them

### 🐬 MySQL

A widely used **relational database** (SQL). Stores data in tables with rows and columns. Best for structured data with clear relationships — users, orders, products.

**Install:**
```bash
sudo apt install mysql-server
sudo mysql_secure_installation
```

**When to use it:**
- PHP/Laravel backends (the traditional LAMP stack)
- Projects that need strict schema enforcement
- When your team or client already uses MySQL in production

**`.env` connection string:**
```
DATABASE_URL=mysql://root:password@localhost:3306/mydb
```

**Key files:**
- Config: `/etc/mysql/mysql.conf.d/mysqld.cnf`
- Data: `/var/lib/mysql/`
- Logs: `/var/log/mysql/error.log`

**Common commands:**
```bash
mysql -u root -p
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
- Node.js/Express backends with Prisma or Knex (your DIETA project uses this)
- When you need JSON columns, arrays, or advanced indexing
- Anything going to production on a serious stack

**`.env` connection string:**
```
DATABASE_URL=postgresql://postgres:password@localhost:5432/mydb
# Prisma format:
DATABASE_URL="postgresql://USER:PASSWORD@localhost:5432/mydb?schema=public"
```

**Key files:**
- Config: `/etc/postgresql/<version>/main/postgresql.conf`
- Data: `/var/lib/postgresql/`

**Common commands:**
```bash
sudo -u postgres psql
\l                        # list databases
CREATE DATABASE myapp;
\c myapp                  # connect
\dt                       # list tables
```

---

### 🍃 MongoDB

A **document database** — stores data as JSON-like documents instead of rows and columns. Schema is flexible; documents in the same collection can have different fields.

**Install:**
```bash
curl -fsSL https://www.mongodb.org/static/pgp/server-7.0.asc \
  | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] \
  https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" \
  | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt update && sudo apt install -y mongodb-org
```

**When to use it:**
- Node.js/Express APIs with Mongoose
- Projects where the data shape changes often (rapid prototyping)
- Your TRISHA backend and HR Attendance API use MongoDB Atlas — run a local instance during development to avoid hitting your cloud quota

**`.env` connection string:**
```
MONGODB_URI=mongodb://localhost:27017/mydb
# With auth:
MONGODB_URI=mongodb://user:password@localhost:27017/mydb
```

**Key files:**
- Config: `/etc/mongod.conf`
- Data: `/var/lib/mongodb/`
- Logs: `/var/log/mongodb/mongod.log`

**Common commands:**
```bash
mongosh
show dbs
use myapp
db.users.find()
db.users.insertOne({ name: "Ian" })
```

---

### 🔴 Redis

An **in-memory key-value store** — extremely fast because everything lives in RAM. Used as a cache, session store, message broker, or pub/sub system.

**Install:**
```bash
sudo apt install redis-server
```

**When to use it:**
- Caching expensive database queries (store result in Redis with a TTL, skip the DB hit)
- Storing session tokens or JWT blocklists
- Rate limiting API endpoints (increment a counter per IP per minute)
- Background job queues (BullMQ, Agenda)

**`.env` connection string:**
```
REDIS_URL=redis://localhost:6379
# With password:
REDIS_URL=redis://:password@localhost:6379
```

**Key files:**
- Config: `/etc/redis/redis.conf`

**Common commands:**
```bash
redis-cli
SET mykey "hello"
GET mykey
TTL mykey
KEYS *               # list all keys (avoid on production)
FLUSHDB              # clear current database
```

---

### 🐳 Docker

A **container runtime** — packages an app and all its dependencies into an isolated container that runs the same everywhere. No more "it works on my machine."

**Install:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER    # run Docker without sudo (re-login after)
```

**When to use it:**
- Running databases without installing them natively (`docker run -d -p 5432:5432 postgres`)
- Keeping projects isolated from your host system
- Deploying apps — build an image once, run it anywhere
- Running GUI tools (Adminer, pgAdmin, Mongo Express, Mailhog) without polluting your machine

**Key commands:**
```bash
docker ps                          # list running containers
docker images                      # list local images
docker compose up -d               # start all services from docker-compose.yml
docker compose down                # stop and remove containers
docker logs <container>            # view container output
docker exec -it <container> bash   # shell into a running container
```

**docker-compose.yml example** (Node + MongoDB + Redis):
```yaml
services:
  app:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - mongo
      - redis
    environment:
      - MONGODB_URI=mongodb://mongo:27017/mydb
      - REDIS_URL=redis://redis:6379

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

A high-performance **web server and reverse proxy**. Sits in front of your apps and routes public traffic to them.

**Install:**
```bash
sudo apt install nginx
```

**Common uses:**

**Reverse proxy** — expose your Node app on port 80 instead of 3000:
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
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

**SSL with Let's Encrypt (free):**
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

**Key commands:**
```bash
sudo nginx -t                    # test config before applying
sudo systemctl reload nginx      # apply config without downtime
```

**Key paths:**

| Path | Purpose |
|---|---|
| `/etc/nginx/nginx.conf` | Main config |
| `/etc/nginx/sites-available/` | Write your site configs here |
| `/etc/nginx/sites-enabled/` | Symlink active configs here |
| `/var/log/nginx/access.log` | All incoming requests |
| `/var/log/nginx/error.log` | Errors and warnings |

**Activate a config:**
```bash
sudo ln -s /etc/nginx/sites-available/myapp /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

### 📂 FileZilla

A **FTP/SFTP client** for transferring files between your local machine and remote servers. Not a system service — it's a regular desktop app. The panel has a dedicated launcher button for it.

**Install:**
```bash
sudo apt install filezilla
```

**When to use it:**
- Uploading build artifacts to a VPS manually
- Managing files on a remote server over SFTP (more visual than `scp`)
- Browsing and editing remote files during deployment debugging
- Connecting to hosting providers that only offer FTP access

**Quick connect:** In FileZilla, use the quickconnect bar at the top:
- Host: `sftp://your-server-ip`
- Username / Password: your SSH credentials
- Port: `22` (SFTP) or `21` (FTP)

> For VPS access, SFTP over port 22 is the secure choice. FTP (port 21) sends credentials in plaintext — avoid it unless the server forces it.

---

## Recommended local dev setup

Only run what the current project actually needs:

| Stack | Services to run |
|---|---|
| Node + MongoDB (e.g. TRISHA backend) | MongoDB, Redis (optional) |
| Node + PostgreSQL + Prisma (e.g. DIETA) | PostgreSQL, Redis (optional) |
| Fully containerized project | Docker only |
| Frontend only (Vite dev server) | Nothing — Vite handles its own server |
| Deploying / testing a domain locally | Nginx + your backend service |

> Keep autostart **disabled** for everything you don't use daily. Start only what the current project needs — this keeps RAM free and avoids port conflicts across projects.

---

## Troubleshooting

### "not installed" shown for a service

The service binary isn't on your system yet. Install it using the commands in the relevant section above, then click **↻ Refresh All**.

### Port shows ○ but status shows running

The service started but crashed immediately (common with config errors). Check the logs with the **📋 logs** button, or run:

```bash
sudo journalctl -u <service> -n 30 --no-pager
```

### pkexec popup doesn't appear

On some setups `pkexec` requires a running polkit agent:

```bash
systemctl status polkit
sudo systemctl start polkit
```

### Port already in use at startup

If a service fails to start, something else may already be on its port:

```bash
sudo ss -tulpn | grep <port>    # e.g. grep 3306 for MySQL
```

Kill the conflicting process or stop the other service first.

### Log window shows no output

Some services write to their own log files instead of journald:

```bash
sudo tail -f /var/log/mysql/error.log
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/mongodb/mongod.log
```

### FileZilla shows "not installed" when clicked

Install it:
```bash
sudo apt install filezilla
```

Then click the button again — no panel restart needed.