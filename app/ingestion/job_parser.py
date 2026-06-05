import re


class JobParser:

    def parse_job_description(self, text: str) -> dict:
        result = {
            "title": "",
            "company": "",
            "location": "",
            "seniority_level": "",
            "requirements": [],
            "nice_to_have": [],
            "responsibilities": [],
            "salary_range": "",
            "skills_detected": [],
        }

        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if lines:
            result["title"] = lines[0]

        if len(lines) > 1:
            result["company"] = lines[1]

        location_pattern = r"(?:based in|location[:\s]*|located in)\s*(.+?)(?:\.|$)"
        location_match = re.search(location_pattern, text, re.IGNORECASE)
        if location_match:
            result["location"] = location_match.group(1).strip()
        else:
            for line in lines[:5]:
                if re.search(r"(remote|hybrid|on-site|onsite|city|state|country)", line, re.IGNORECASE):
                    result["location"] = line
                    break

        result["seniority_level"] = self._extract_seniority(text)

        section_headers = {
            "requirements": r"(?:requirements|qualifications|must have|required skills|what you(?:'ll| will) need)",
            "nice_to_have": r"(?:nice to have|preferred|desirable|bonus|plus|good to have)",
            "responsibilities": r"(?:responsibilities|what you(?:'ll| will) do|role description|about the role|key duties|duties)",
        }

        for key, pattern in section_headers.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                rest = text[match.end():]
                next_section = re.search(
                    r"\n\s*(?:requirements|qualifications|nice to have|preferred|responsibilities|what you(?:'ll| will) (?:do|need)|benefits|salary|perks|about us|company|how to apply|application)",
                    rest,
                    re.IGNORECASE,
                )
                section_text = rest[: next_section.start()] if next_section else rest
                items = self._extract_list_items(section_text)
                result[key] = items

        salary_pattern = r"\$[\d,]+(?:\s*[-–to]+\s*\$[\d,]+)?(?:\s*(?:per|a|/)\s*(?:year|annum|hour|month|hr|mo|yr))?"
        salary_match = re.search(salary_pattern, text, re.IGNORECASE)
        if salary_match:
            result["salary_range"] = salary_match.group(0).strip()

        result["skills_detected"] = self._extract_skills(text)

        return result

    def parse_from_url(self, url: str) -> dict:
        return {}

    def _extract_seniority(self, text: str) -> str:
        lower = text.lower()
        seniority_levels = [
            ("principal", ["principal", "distinguished", "fellow"]),
            ("director", ["director"]),
            ("vp", ["vice president", "vp"]),
            ("senior", ["senior", "sr.", "sr "]),
            ("lead", ["lead", "staff"]),
            ("mid", ["mid-level", "intermediate"]),
            ("junior", ["junior", "jr.", "jr ", "entry level", "entry-level", "associate"]),
        ]
        for level, keywords in seniority_levels:
            for keyword in keywords:
                if keyword in lower:
                    return level
        return "mid"

    def _extract_skills(self, text: str) -> list:
        skill_patterns = [
            r"\b(?:Python|Java|JavaScript|TypeScript|Go|Golang|Rust|C\+\+|C#|Ruby|PHP|Swift|Kotlin|Scala|R)\b",
            r"\b(?:React|Angular|Vue|Vue\.js|Next\.js|Nuxt|Svelte|Node\.js|Express|Django|Flask|FastAPI|Spring Boot|Rails)\b",
            r"\b(?:AWS|Azure|GCP|Google Cloud|IBM Cloud|Oracle Cloud|DigitalOcean)\b",
            r"\b(?:Docker|Kubernetes|K8s|Terraform|Ansible|Puppet|Chef|Jenkins|GitHub Actions|GitLab CI|CircleCI|ArgoCD|Spinnaker)\b",
            r"\b(?:PostgreSQL|MySQL|MongoDB|Redis|Elasticsearch|Cassandra|DynamoDB|CouchDB|Neo4j|MariaDB|SQL Server|Oracle DB)\b",
            r"\b(?:Kafka|RabbitMQ|ActiveMQ|NATS|Pulsar)\b",
            r"\b(?:GraphQL|REST|gRPC|WebSocket|SOAP)\b",
            r"\b(?:Linux|Unix|Windows Server|macOS)\b",
            r"\b(?:HTML|CSS|SASS|LESS|Tailwind)\b",
            r"\b(?:TensorFlow|PyTorch|scikit-learn|Pandas|NumPy|NLP|LLM|Machine Learning|Deep Learning|AI|Artificial Intelligence|Computer Vision)\b",
            r"\b(?:CI/CD|DevOps|SRE|Site Reliability|Agile|Scrum|Kanban|SAFe)\b",
            r"\b(?:Cybersecurity|SIEM|SOC|Penetration Testing|Zero Trust|IAM|OAuth|SAML)\b",
            r"\b(?:Data Engineering|ETL|Apache Spark|Airflow|dbt|Snowflake|Databricks|Redshift|BigQuery|Looker|Tableau|Power BI)\b",
            r"\b(?:Microservices|Serverless|Event-Driven|Domain-Driven Design|DDD|12-Factor)\b",
            r"\b(?:PMP|ITIL|TOGAF|COBIT|Six Sigma|CSM|SAFe|AWS Solutions Architect|AWS DevOps|Azure Architect|GCP Professional|CISSP|CISM|CISA|CompTIA)\b",
            r"\b(?:PowerShell|Bash|Shell Scripting|Terraform HCL|CloudFormation|YAML|JSON)\b",
        ]

        skills = set()
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill = match.strip()
                if len(skill) > 1:
                    normalized = skill.lower().replace(" ", " ").strip()
                    skills.add(normalized)

        return sorted(skills)

    def _extract_list_items(self, text: str) -> list:
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            cleaned = re.sub(r"^[\-\•\*\d+\.\)\]]+\s*", "", line).strip()
            if cleaned and len(cleaned) > 3:
                items.append(cleaned)
        return items
