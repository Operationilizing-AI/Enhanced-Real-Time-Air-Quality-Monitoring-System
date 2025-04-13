# Phase 1: Interim Deliverables
In this first phase, you'll experiment with different modeling approaches and plan your system architecture.


## Tasks:

### Model Experimentation with MLFlow:

Option A (Recommended for most teams): Select the best-performing model from your individual assignments and enhance it with additional features or parameter tuning
Option B: Create an ensemble combining multiple models
Option C: Develop a completely new model'

### MLFlow Setup (Step-by-Step):
Install MLFlow: pip install mlflow
Start MLFlow tracking server: mlflow ui --backend-store-uri sqlite:///mlflow.db

### System Architecture Design (10 points):
Clarification: Your architecture should include these components at minimum:
- Kafka producer and consumer
- Model training pipeline with MLFlow
- Model serving API
- Monitoring dashboard

### Project Plan (5 points):
- Create a timeline with specific milestones
- Assign roles based on team member strengths
- Identify which team members will focus on learning which technologies


## Deliverables:

Interim Report (15-20 pages):
- Model experimentation results
- System architecture diagram
- Project plan and timeline
  
Code Repository:
- Initial MLFlow experiments
- Preliminary feature engineering code
- README with setup instructions
