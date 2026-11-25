"""Builds placeiq/extraction/taxonomy.json. Edit SRC, then: python scripts/build_taxonomy.py placeiq/extraction/taxonomy.json

Line format: canonical | alias1, alias2 | StrictAlias (case-sensitive, exact match only)
Keep ambiguous English words (excel, express, go, rest, spring) out of plain aliases."""
import json, sys

SRC = {
"programming": """
haskell |
elixir |
lua |
julia |
assembly | assembly language, x86 assembly
objective-c | objective c
groovy |
fortran |
cobol |
vba | excel vba
python | python3
java | core java, java8, java 8
javascript | js, ecmascript, es6
typescript |
c | c programming, c language | C
c++ | cpp, c plus plus
c# | csharp, c sharp
go | golang | Go
rust | rust lang
kotlin |
swift |
r | r programming, r language | R
scala |
php |
ruby |
dart |
matlab |
bash | shell scripting, shell script, bash scripting
perl |
solidity |
""",
"web_frontend": """
material ui | material-ui, mui
chakra ui |
three.js | threejs
d3.js | d3js, d3
web accessibility | wcag, a11y
responsive design | responsive web design
progressive web apps | pwa
web performance | lighthouse
nuxt.js | nuxtjs
gatsby |
html | html5
css | css3
react | reactjs, react js, react.js
angular | angularjs, angular js
vue | vuejs, vue js, vue.js
next.js | nextjs, next js
svelte |
redux |
tailwind css | tailwind, tailwindcss
bootstrap |
jquery |
sass | scss
webpack |
vite |
""",
"web_backend": """
nestjs | nest.js
spring security |
jwt | json web token, json web tokens
oauth | oauth2, oauth 2.0
swagger | openapi
rabbitmq |
celery |
gunicorn |
api gateway |
webrtc |
mern stack | mern
mean stack |
jsp | servlets, jsp servlets
node.js | node, nodejs, node js
express | expressjs, express js, express.js | Express
django |
flask |
fastapi | fast api
spring boot | springboot, spring framework, spring mvc
hibernate |
asp.net | asp net, dotnet, .net, dot net
laravel |
ruby on rails | rails
rest api | restful, restful api, rest apis, restful apis
graphql |
grpc |
microservices | microservice, micro services
websockets | websocket, socket.io
""",
"databases": """
mariadb |
microsoft sql server | mssql, sql server, t-sql, tsql
supabase |
prisma |
sequelize |
mongoose |
sqlalchemy |
database design | er diagrams, schema design, normalization
pinecone |
vector databases | vector database, chromadb, faiss
sql | structured query language
mysql |
postgresql | postgres, postgre sql
mongodb | mongo
sqlite |
oracle database | oracle db, oracle sql, pl/sql, plsql
redis |
cassandra |
firebase |
dynamodb |
elasticsearch | elastic search
nosql |
neo4j |
""",
"data_science": """
hypothesis testing | a/b testing, ab testing
probability |
linear algebra |
regression analysis | linear regression, logistic regression
r studio | rstudio
spss |
looker |
google sheets |
data cleaning | data wrangling, data preprocessing
feature engineering |
streamlit |
data analysis | data analytics
data visualization | data visualisation
statistics | statistical analysis
pandas |
numpy |
matplotlib |
seaborn |
plotly |
scipy |
excel | ms excel, microsoft excel, advanced excel | Excel
power bi | powerbi
tableau |
jupyter | jupyter notebook
eda | exploratory data analysis
""",
"ml_ai": """
random forest | random forests
decision trees | decision tree
support vector machines | svm
k-means | kmeans, k means clustering
clustering |
classification |
yolo | yolov5, yolov8
object detection |
image processing |
speech recognition |
transformers architecture | attention mechanism
bert |
gpt | chatgpt api, openai api
prompt engineering |
rag | retrieval augmented generation
fine-tuning | fine tuning, finetuning
mlops |
mlflow |
onnx |
explainable ai | xai, shap
nltk |
spacy |
gensim |
machine learning | ml
deep learning | dl
natural language processing | nlp
computer vision | opencv
scikit-learn | sklearn, scikit learn
tensorflow |
keras |
pytorch |
xgboost |
lightgbm |
hugging face | huggingface, transformers
large language models | llm, llms
generative ai | genai, gen ai
langchain |
reinforcement learning |
neural networks | neural network, cnn, rnn, lstm
recommendation systems | recommender systems, recommendation system
time series | time series analysis, forecasting
""",
"data_engineering": """
dbt |
apache flink | flink
apache hive | hive
data pipelines | data pipeline
data modeling | data modelling
aws glue |
redshift |
apache spark | spark, pyspark
hadoop |
kafka | apache kafka
airflow | apache airflow
etl | etl pipelines
data warehousing | data warehouse
snowflake |
databricks |
bigquery |
""",
"cloud_devops": """
aws ec2 | ec2
aws s3 | s3, amazon s3
azure devops |
google kubernetes engine | gke
docker compose | docker-compose
helm |
prometheus |
grafana |
elk stack | kibana, logstash
cloudformation |
openshift |
netlify |
digitalocean |
site reliability engineering | sre
aws | amazon web services
azure | microsoft azure
gcp | google cloud, google cloud platform
docker |
kubernetes | k8s
jenkins |
ci/cd | ci cd, cicd, continuous integration
terraform |
ansible |
github actions |
linux | ubuntu, unix
nginx |
serverless | aws lambda
heroku |
vercel |
""",
"tools": """
bitbucket |
confluence |
trello |
notion | notion.so | Notion
intellij idea | intellij
eclipse |
android studio |
xcode |
latex | overleaf
canva |
git | version control
github |
gitlab |
jira |
postman |
figma |
vs code | vscode, visual studio code
""",
"mobile": """
swiftui |
xamarin |
ionic |
android | android development
ios | ios development
flutter |
react native |
jetpack compose |
""",
"cs_fundamentals": """
compiler design | compilers
theory of computation | automata theory, automata
computer architecture | computer organization, coa
distributed systems |
concurrency | multithreading, multi-threading
discrete mathematics |
graph algorithms | dynamic programming, greedy algorithms
low latency systems |
data structures | dsa, data structure
algorithms | algorithm, algorithm design
object oriented programming | oop, oops, object oriented
operating systems | operating system
computer networks | computer networking, networking
dbms | database management systems, database management system
system design | low level design, high level design, lld, hld
competitive programming | leetcode, codeforces, codechef
design patterns |
software engineering | sdlc
agile | scrum
""",
"testing": """
cypress |
playwright |
testng |
mocha |
postman testing | api testing
performance testing | jmeter, load testing
test driven development | tdd
unit testing | unit tests
selenium |
jest |
pytest |
junit |
manual testing |
automation testing | test automation
""",
"security": """
owasp | owasp top 10
wireshark |
burp suite |
metasploit |
kali linux |
vulnerability assessment | vapt
siem | splunk
cybersecurity | cyber security, information security
network security |
penetration testing | pentesting, ethical hacking
cryptography |
""",
"hardware_embedded": """
microcontrollers | microcontroller, 8051, avr
esp32 | esp8266
plc | plc programming
pcb design | altium, kicad
matlab simulink | simulink
labview |
fpga |
signal processing | dsp, digital signal processing
robotics | ros
ansys |
catia |
embedded systems | embedded
arduino |
raspberry pi |
iot | internet of things
vlsi |
verilog |
autocad |
solidworks |
""",
"blockchain": """
ethereum |
smart contracts | smart contract
hyperledger |
blockchain |
web3 |
""",
"design_product": """
ui/ux design | ui ux, ui/ux, ux design, ui design, user experience
adobe xd |
photoshop | adobe photoshop
illustrator | adobe illustrator
wireframing | prototyping
product management |
""",
"business_domain": """
erp | sap
salesforce |
crm |
fintech |
digital marketing | seo, sem
business analysis | business analyst, requirements gathering
""",
}

tax = {}
for cat, block in SRC.items():
    for line in block.strip().splitlines():
        parts = [p.strip() for p in line.split("|")]
        canon = parts[0]
        aliases = [a.strip() for a in parts[1].split(",") if a.strip()] if len(parts) > 1 else []
        strict = [a.strip() for a in parts[2].split(",") if a.strip()] if len(parts) > 2 else []
        if canon in tax:
            sys.exit(f"duplicate {canon}")
        if canon not in ("c", "r", "go", "express", "excel", "notion"):
            aliases = [canon] + [a for a in aliases if a != canon]
        entry = {"category": cat, "aliases": aliases}
        if strict:
            entry["strict"] = strict
        tax[canon] = entry

# alias collision check
seen = {}
for c, e in tax.items():
    for a in e["aliases"]:
        if a in seen:
            sys.exit(f"alias {a} in {seen[a]} and {c}")
        seen[a] = c
json.dump(tax, open(sys.argv[1], "w", encoding="utf-8"), indent=1)
print(len(tax), "skills,", len(seen), "aliases")
