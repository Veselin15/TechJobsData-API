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

# 7. Skill aliases — source tags come in many spellings; map them onto the
# canonical names used in TECH_KEYWORDS so "golang", "Go" and "GO" all count
# as one skill. Keys must be lowercase.
SKILL_ALIASES = {
    "golang": "Go",
    "js": "JavaScript",
    "javascript es6": "JavaScript",
    "ts": "TypeScript",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "reactjs": "React",
    "react js": "React",
    "react.js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "nextjs": "Next.js",
    "next": "Next.js",
    "nuxt": "Nuxt.js",
    "angularjs": "Angular",
    "postgres": "PostgreSQL",
    "postgre": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "k8s": "Kubernetes",
    "kube": "Kubernetes",
    "amazon web services": "AWS",
    "google cloud platform": "GCP",
    "gcloud": "GCP",
    "ms azure": "Azure",
    "microsoft azure": "Azure",
    "c sharp": "C#",
    "csharp": "C#",
    "cpp": "C++",
    "c plus plus": "C++",
    "dotnet": ".NET Core",
    ".net": ".NET Core",
    "rails": "Ruby on Rails",
    "ror": "Ruby on Rails",
    "ml": "Machine Learning",
    "ai": "Artificial Intelligence",
    "artificial intelligence (ai)": "Artificial Intelligence",
    "large language models": "LLM",
    "llms": "LLM",
    "genai": "Generative AI",
    "gen ai": "Generative AI",
    "nlp (natural language processing)": "NLP",
    "natural language processing": "NLP",
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "tf": "TensorFlow",
    "ci/cd pipelines": "CI/CD",
    "cicd": "CI/CD",
    "ci cd": "CI/CD",
    "restful api": "REST API",
    "restful apis": "REST API",
    "rest apis": "REST API",
    "rest": "REST API",
    "springboot": "Spring Boot",
    "spring": "Spring Boot",
    "tailwind": "Tailwind CSS",
    "tailwindcss": "Tailwind CSS",
    "es": "Elasticsearch",
    "elastic search": "Elasticsearch",
    "wp": "WordPress",
    "react-native": "React Native",
    "react native development": "React Native",
    "sre (site reliability engineering)": "SRE",
    "site reliability": "SRE",
    "devops engineer": "CI/CD",
    "gh actions": "GitHub Actions",
    "sass/scss": "Sass",
    "scss": "Sass",
}

# 8. Noise tags — generic source tags that are not skills; never store them.
# Lowercase, matched after alias resolution.
NOISE_TAGS = {
    "dev", "developer", "development", "engineer", "engineering", "software",
    "software development", "tech", "technology", "it", "digital nomad",
    "remote", "remote work", "work from home", "wfh", "hybrid", "onsite",
    "full time", "full-time", "part time", "part-time", "contract",
    "freelance", "internship", "job", "jobs", "career", "careers", "hiring",
    "urgent", "startup", "senior", "junior", "mid", "lead", "manager",
    "english", "german", "french", "spanish", "benefits", "equity", "401k",
    "health insurance", "salary", "competitive salary", "other", "misc",
    "non tech", "non-tech", "web", "backend", "back-end", "back end",
    "frontend", "front-end", "front end", "full stack", "fullstack",
    "full-stack", "code", "coding", "computer science", "team player",
    "communication", "growth", "flexible hours", "apply now",
}

# 9. Title noise — decorations recruiters add to titles that carry no signal.
# Applied in order by clean_title().
TITLE_NOISE_PATTERNS = [
    r'\((?:m/f/d|f/m/d|w/m/d|m/w/d|m/f/x|f/m/x|m/w/x|w/m/x|all genders?|h/f|f/h)\)',
    r'\b(?:m/f/d|f/m/d|w/m/d|m/w/d|m/f/x|f/m/x)\b',
    r'\((?:remote|100%\s*remote|fully\s*remote|hybrid|on-?site)[^)]*\)',
    r'\[(?:remote|hybrid|on-?site|hiring)[^\]]*\]',
    r'(?:^|\s)[-–—|/]\s*(?:100%\s*)?remote\s*$',
    r'^\s*(?:urgent|hiring|now hiring|hot)\s*[:!-]\s*',
    r'[\U0001F300-\U0001FAFF☀-➿️]',  # emoji & dingbats
]

# 10. Work-model detection (remote / hybrid / on-site)
HYBRID_PATTERNS = [r'\bhybrid\b', r'\d\s*days?\s+(?:per\s+week\s+)?(?:in|at)\s+(?:the\s+)?office']
ONSITE_PATTERNS = [r'\bon-?site\b', r'\bin-?office\b', r'\bin person\b', r'\brelocation required\b']
REMOTE_PATTERNS = [r'\bremote\b', r'\bwork from home\b', r'\bwork from anywhere\b',
                   r'\bdistributed team\b', r'\btelecommute\b', r'\bwfh\b']

# 11. Employment-type detection
EMPLOYMENT_PATTERNS = {
    'Internship': [r'\binternship\b', r'\bintern\b', r'\bworking student\b', r'\bwerkstudent\b'],
    'Freelance': [r'\bfreelancer?\b', r'\bself-?employed\b'],
    'Contract': [r'\bcontract(?:or)?\b', r'\bfixed[- ]term\b', r'\bb2b\b', r'\btemporary\b',
                 r'\b\d+[- ]months? contract\b'],
    'Part-time': [r'\bpart[- ]time\b'],
    'Full-time': [r'\bfull[- ]time\b', r'\bpermanent\b', r'\bunbefristet\b'],
}

# 12. Role categories — ordered: first match on the title wins, then skills
# vote. Patterns are regexes tested against the lowercase title.
ROLE_CATEGORY_TITLE_RULES = [
    ("DevOps & SRE", [r'devops', r'\bsre\b', r'site reliability', r'platform engineer',
                      r'infrastructure', r'cloud engineer', r'cloud architect', r'systems? engineer']),
    ("Data & ML", [r'\bdata\b', r'machine learning', r'\bml\b', r'\bai\b', r'deep learning',
                   r'analytics', r'analyst', r'business intelligence', r'\bbi\b',
                   r'nlp', r'computer vision', r'research scientist', r'llm']),
    ("Security", [r'security', r'penetration', r'pentest', r'appsec', r'infosec', r'\bsoc\b',
                  r'cyber']),
    ("QA & Testing", [r'\bqa\b', r'quality assurance', r'test(?:er|ing)?\b', r'automation engineer',
                      r'\bsdet\b']),
    ("Mobile", [r'\bios\b', r'android', r'mobile', r'flutter', r'react native']),
    ("Frontend", [r'front[- ]?end', r'\bui developer\b', r'react developer', r'angular developer',
                  r'vue', r'web designer']),
    ("Backend", [r'back[- ]?end', r'\bapi\b', r'python developer', r'java developer',
                 r'php developer', r'ruby developer', r'golang', r'\bgo developer\b',
                 r'node', r'\.net', r'c# developer', r'rust developer', r'elixir']),
    ("Full-Stack", [r'full[- ]?stack', r'web developer', r'software engineer', r'software developer']),
    ("Design", [r'designer', r'\bux\b', r'\bui/ux\b', r'product design']),
    ("Product & Management", [r'product manager', r'product owner', r'project manager',
                              r'scrum master', r'engineering manager', r'\bcto\b',
                              r'head of', r'director']),
    ("Embedded & Hardware", [r'embedded', r'firmware', r'hardware', r'\biot\b', r'robotics',
                             r'\bfpga\b']),
    ("Blockchain", [r'blockchain', r'web3', r'solidity', r'smart contract', r'crypto']),
]

# Skills that strongly indicate a category — used when the title is generic.
ROLE_CATEGORY_SKILL_HINTS = {
    "DevOps & SRE": {"Kubernetes", "Terraform", "Ansible", "Docker", "Jenkins", "Prometheus",
                     "Grafana", "Helm", "ArgoCD", "SRE", "Istio", "Vault", "CI/CD"},
    "Data & ML": {"Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Pandas",
                  "NumPy", "Scikit-learn", "Data Science", "Spark", "Airflow", "Databricks",
                  "Snowflake", "BigQuery", "NLP", "LLM", "Tableau", "Power BI"},
    "Frontend": {"React", "Angular", "Vue.js", "Next.js", "Svelte", "Tailwind CSS", "CSS",
                 "Sass", "Redux", "Vite", "Webpack"},
    "Backend": {"Django", "Flask", "FastAPI", "Spring Boot", "Laravel", "Ruby on Rails",
                "NestJS", "Express", "ASP.NET", ".NET Core", "Phoenix", "gRPC"},
    "Mobile": {"Flutter", "React Native", "SwiftUI", "Jetpack Compose", "Android", "iOS",
               "Kotlin", "Swift"},
    "QA & Testing": {"Selenium", "Playwright", "Cypress", "Pytest", "Jest", "JUnit"},
    "Blockchain": {"Solidity", "Web3", "Ethereum", "Blockchain"},
}

# 13. Fixed reference rates for cross-currency comparison. These are
# deliberately static (updated with releases): the goal is comparable
# magnitudes for sorting/analytics, not exchange-rate precision.
CURRENCY_TO_USD = {
    "USD": 1.0,
    "EUR": 1.09,
    "GBP": 1.27,
    "BGN": 0.56,
    "AUD": 0.66,
    "CAD": 0.73,
    "CHF": 1.13,
    "PLN": 0.25,
    "SEK": 0.095,
    "NOK": 0.093,
    "DKK": 0.146,
    "INR": 0.012,
    "JPY": 0.0067,
}

# 14. Description boilerplate headings — summaries should skip past these to
# the first sentence that says something about the actual role.
SUMMARY_BOILERPLATE_PATTERNS = [
    r'^about (?:us|the (?:company|team|role|job|position)|[\w\s&.,-]{2,40})[:\s]*$',
    r'^(?:who|what) we (?:are|do)[:\s]*$',
    r'^(?:the )?(?:role|position|opportunity|company|team)[:\s]*$',
    r'^job (?:description|summary|overview)[:\s]*$',
    r'^(?:overview|description|summary|introduction)[:\s]*$',
    r'^headquarters?[:\s]', r'^url[:\s]', r'^location[:\s]',
]

# 15. Skill names that are also everyday English words. Extracted from prose
# only when the surrounding text looks technical — otherwise German listings
# saying 'das "Go" geben' or English ones saying "ready to go" get tagged
# with the Go language (this actually happened: 154 of 1,066 jobs).
AMBIGUOUS_PROSE_SKILLS = {
    "go", "r", "c", "dart", "shell", "ray", "spark", "chef", "puppet",
    "express", "unity", "rust", "flask",
}

# Words that mark a context window as "technical" for the check above.
TECH_CONTEXT_PATTERN = (
    r'develop|engineer|program|language|backend|frontend|full.?stack|'
    r'microservice|framework|experience|proficien|knowledge|stack|coding|'
    r'\bcode\b|\bapi\b|\bsdk\b|written in|database|server|script|'
    r'kubernetes|docker|cloud|distributed|concurren'
)
