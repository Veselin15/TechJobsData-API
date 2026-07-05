# scraper_service/scraper_service/constants.py

# 1. Expanded Tech Keywords (Languages, Frameworks, Cloud, Tools)
TECH_KEYWORDS = [
    # Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust", "Ruby", "PHP",
    "Swift", "Kotlin", "Dart", "Scala", "Elixir", "Haskell", "Lua", "Perl", "R", "Julia",
    "Bash", "Shell", "PowerShell", "SQL", "HTML", "CSS", "Sass", "Less",

    # Web Frameworks
    "Django", "Flask", "FastAPI", "React", "Angular", "Vue.js", "Next.js", "Nuxt.js",
    "Svelte", "Node.js", "Express", "NestJS", "Spring Boot", "ASP.NET", ".NET Core",
    "Laravel", "Symfony", "Ruby on Rails", "Phoenix", "jQuery", "Bootstrap", "Tailwind CSS",

    # Mobile
    "React Native", "Flutter", "Android", "iOS", "SwiftUI", "Jetpack Compose", "Xamarin", "Ionic",

    # Database & Storage
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra", "MariaDB",
    "SQLite", "DynamoDB", "Cosmos DB", "Neo4j", "Oracle", "SQL Server", "Firebase", "Supabase",

    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Google Cloud", "Docker", "Kubernetes", "Terraform", "Ansible",
    "Jenkins", "GitLab CI", "GitHub Actions", "CircleCI", "Travis CI", "Puppet", "Chef",
    "Prometheus", "Grafana", "Datadog", "New Relic", "Splunk", "ELK Stack", "Nginx", "Apache",

    # AI & Data
    "Machine Learning", "Deep Learning", "Data Science", "Artificial Intelligence", "NLP",
    "Computer Vision", "TensorFlow", "PyTorch", "Keras", "Scikit-learn", "Pandas", "NumPy",
    "Matplotlib", "Seaborn", "OpenCV", "Hugging Face", "LLM", "Generative AI", "Spark", "Hadoop",
    "Airflow", "Databricks", "Snowflake", "BigQuery", "Redshift", "Tableau", "Power BI",

    # Messaging & Streaming
    "Kafka", "RabbitMQ", "Celery", "ActiveMQ", "SQS", "Pub/Sub", "NATS",

    # Testing & Automation
    "Selenium", "Playwright", "Cypress", "Jest", "Pytest", "JUnit", "Mocha",
    "Scrapy", "Puppeteer",

    # Frontend Tooling
    "Vite", "Webpack", "Redux", "Zustand", "Remix", "Astro", "Storybook",
    "Deno", "Bun", "Electron",

    # AI Ecosystem (modern)
    "LangChain", "OpenAI", "Anthropic", "RAG", "MLOps", "Vector Database",
    "Pinecone", "Weaviate", "MLflow", "Kubeflow", "Ray", "ETL",

    # Blockchain & Games
    "Solidity", "Web3", "Blockchain", "Ethereum", "Unity", "Unreal Engine", "Godot",

    # Enterprise & Platforms
    "Salesforce", "SAP", "ServiceNow", "Shopify", "WordPress", "Magento", "Stripe",
    "Vercel", "Netlify", "Heroku", "DigitalOcean", "Cloudflare",

    # Tools & Concepts
    "Git", "GitHub", "GitLab", "Bitbucket", "Jira", "Confluence", "Slack", "Trello", "Asana",
    "Agile", "Scrum", "Kanban", "TDD", "BDD", "CI/CD", "REST API", "GraphQL", "gRPC",
    "WebSockets", "Microservices", "Serverless", "Linux", "Unix", "Ubuntu", "CentOS",
    "OAuth", "SSO", "Cybersecurity", "Penetration Testing", "SRE", "Observability",
    "OpenTelemetry", "Vault", "Istio", "Helm", "ArgoCD"
]

# 2. Negation Phrases (Phrases that indicate a skill is NOT required)
NEGATION_PATTERNS = [
    r"no experience",
    r"not required",
    r"not mandatory",
    r"no knowledge",
    r"don't need",
    r"without experience",
    r"no prior experience",
    r"is a plus",  # Often means "nice to have" but not strict requirement for the core role
    r"would be an asset",
    r"desirable but not",
    r"advantageous",
]

# 3. Seniority Patterns (Ranked by priority)
SENIORITY_MAP = {
    "Lead": [
        r"lead", r"principal", r"head of", r"manager", r"director", r"vp",
        r"chief", r"architect", r"founding", r"staff engineer"
    ],
    "Senior": [
        r"senior", r"sr\.", r"sr ", r"expert", r"advanced", r"experienced"
    ],
    "Junior": [
        r"junior", r"jr\.", r"jr ", r"entry level", r"entry-level",
        r"graduate", r"intern", r"internship", r"trainee", r"apprentice", r"associate"
    ],
    "Mid-Level": [
        r"mid-level", r"mid level", r"intermediate", r"medior"
    ]
}

# 4. Salary Ignore Terms (Expanded)
SALARY_IGNORE_TERMS = [
    r"people", r"employees", r"staff", r"members", r"users", r"customers",
    r"clients", r"downloads", r"active users", r"followers", r"subscribers",
    r"locations", r"countries", r"cities", r"offices", r"branches",
    r"products", r"services", r"projects", r"applications",
    r"servers", r"nodes", r"requests", r"lines of code",
    r"registered users", r"students", r"graduates", r"partners",

    # --- NEW: Time & Metric units to ignore ---
    r"hours", r"hour", r"hrs", r"days", r"day", r"weeks", r"week",
    r"months", r"month", r"years", r"year",
    r"shifts", r"calls", r"tickets", r"items", r"units"
]

SALARY_HINTS = [
    r"salary", r"salary range", r"compensation", r"remuneration",
    r"pay", r"yearly", r"annually", r"per year", r"per annum",
    r"base", r"package", r"ote", r"earnings",
    # Period hints (crucial for detecting '4000 per month')
    r"per month", r"monthly", r"/mo", r"p\.m\.",
    r"per hour", r"hourly", r"/hr", r"p\.h\.",
    r"per day", r"daily"
]

# 6. Period Multipliers (To convert everything to Annual)
SALARY_MULTIPLIERS = {
    'monthly': [r'per month', r'/\s*month', r'/\s*mo\b', r'monthly', r'p\.m\.'],
    'yearly': [r'per year', r'/\s*year', r'/\s*yr\b', r'yearly', r'annually', r'p\.a\.', r'per annum'],
    'hourly': [r'per hour', r'/\s*hour', r'/\s*hr\b', r'hourly', r'p\.h\.', r'an hour'],
    'daily': [r'per day', r'/\s*day', r'daily']
}
