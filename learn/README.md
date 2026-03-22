# AlphaOneLabs Education Platform

## Project Overview

Alpha One Labs is an education platform designed to facilitate both learning and teaching. The platform provides a comprehensive environment where educators can create and manage courses, while students can learn, collaborate, and engage with peers. With features like study groups, peer connections, and discussion forums, we aim to create a collaborative learning environment that goes beyond traditional online education.

## Tech Stack

- Frontend: HTML,Tailwind CSS 
- Backend: Python (Cloudflare Worker)
- Database: Cloudflare D1 (SQLite)

## Set Up Instructions

### Prerequisites

Make sure you have installed:
 - Node.js
 - Wrangler CLI

Install Wrangler:

```bash
 npm install -g wrangler
```

### Clone the Repository

```bash
 git clone https://github.com/<user_name>/learn.git
 cd learn
```

### Login to Cloudflare (One time)

```bash
 wrangler login
```

### Setup Database (D1)

- Create Database:

```bash
 wrangler d1 create education_db
```

- Add the generated database_id to your wrangler.toml:

```bash
 [[d1_databases]]
 binding = "DB"
 database_name = "education_db"
 database_id = "YOUR_DATABASE_ID"
```

- Apply Schema:

```bash
 wrangler d1 execute education_db --file=schema.sql
```

### Run Backend

```bash
 wrangler dev
```
Backend server will start at :

```bash
 http://127.0.0.1:8787
```

### Run Frontend

- Open directly

```bash
 public/index.html
```

- Use a local server

```bash
 npx serve public
```

Frontend Server will start at:

```bash
 http://localhost:3000
```