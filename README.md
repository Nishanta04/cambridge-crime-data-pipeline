# Cambridge Crime Data Pipeline

An end-to-end data engineering project that collects daily crime incident data from the Cambridge Police Department, processes it, stores it in a PostgreSQL database, and presents the results through an interactive dashboard.

The idea behind this project was to build a pipeline that keeps crime data organised and makes it easier to explore patterns and trends over time without manually processing the data every time.

**Live Dashboard:** [Cambridge Crime Trends](https://cambridge-crime-data-pipeline.streamlit.app/)

## What This Project Does

The pipeline follows four main steps:

1. **Extract:** Fetches crime incident records from the Cambridge Police Department's public dataset using the Socrata API.
2. **Validate:** Checks the incoming data for missing fields, invalid values, and schema issues.
3. **Transform:** Removes duplicate records and extracts useful date and time information such as year, month, day, hour, and day of the week.
4. **Load:** Stores the processed records in a PostgreSQL database using upsert operations to avoid duplicate entries.

The processed data is then used by a Streamlit dashboard to explore crime trends and patterns.

## Tech Stack

- **Python** – Core programming language
- **Pandas** – Data cleaning and transformation
- **Socrata API (Sodapy)** – Data extraction
- **Prefect** – ETL workflow orchestration
- **PostgreSQL (Neon)** – Database
- **SQLAlchemy** – Database operations
- **Streamlit** – Interactive dashboard
- **Plotly** – Data visualization
- **GitHub** – Version control

## Project Structure

```text
cambridge-crime-data-pipeline/
│
├── .github/
│   └── workflows/       # GitHub Actions workflows
│
├── .env.example         # Environment variable template
├── .gitignore
│
├── extract.py           # Fetch data from Socrata API
├── validate.py          # Validate incoming records
├── transform.py         # Clean and transform data
├── load.py              # Load data into PostgreSQL
│
├── etl_pipeline.py      # Main ETL pipeline
├── dashboard.py         # Streamlit dashboard
│
├── requirements.txt     # Python dependencies
└── README.md
```

## Getting Started

If you want to run the project locally, follow these steps.

### 1. Clone the repository

```bash
git clone https://github.com/Nishanta04/cambridge-crime-data-pipeline.git
cd cambridge-crime-data-pipeline
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

**Linux / macOS**
```bash
source .venv/bin/activate
```

**Windows**
```bash
.venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the root directory using `.env.example` as a reference.

```env
DATABASE_URL=your_postgresql_connection_string
SOCRATA_APP_TOKEN=your_socrata_app_token
```

The Socrata app token is optional, but using one helps avoid API request throttling.

For local testing, the pipeline also supports SQLite when `DATABASE_URL` is not provided.

### 5. Run the ETL pipeline

```bash
python etl_pipeline.py
```

This executes the complete workflow:

**Extract → Validate → Transform → Load**

### 6. Run the dashboard

In a separate terminal, activate the virtual environment and run:

```bash
streamlit run dashboard.py
```

The dashboard will be available at:

```text
http://localhost:8501
```

## Dashboard

The dashboard provides an interactive way to explore the processed Cambridge crime data and understand how reported incidents vary over time.

You can access the deployed version here:

[Open Cambridge Crime Trends Dashboard](https://cambridge-crime-data-pipeline.streamlit.app/)

## Data Source

The project uses the Cambridge Police Department Daily Police Log dataset, available through the Socrata Open Data Portal.

[Cambridge Police Department – Daily Police Log](https://data.cambridgema.gov/)

## What I Learned

Building this project helped me get hands-on experience with:

- Designing an end-to-end ETL pipeline.
- Working with public APIs and real-world datasets.
- Implementing data validation and cleaning.
- Handling duplicate records through database upserts.
- Connecting Python applications to PostgreSQL.
- Orchestrating workflows using Prefect.
- Building interactive dashboards with Streamlit and Plotly.

## Author

**Nishanta Makkar**

[GitHub Profile](https://github.com/Nishanta04)
