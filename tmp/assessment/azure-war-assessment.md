# Azure Well-Architected Review — Sentinel Intelligence
**Date:** April 22, 2026  
**Project:** Sentinel Intelligence — GMP Deviation & CAPA Operations Assistant  
**Assessment URL:** https://learn.microsoft.com/en-us/assessments/azure-architecture-review/sessions/e2c98b12-7804-449f-ac6a-e29a797758b8  
**Total Questions:** 61 (all answered)  
**Completed:** ✅ April 22, 2026

---

## Architecture Context

- **Platform:** Azure AI Foundry (multi-agent: Research, Document, Execution)
- **Orchestration:** Azure Durable Functions (Python)
- **Frontend:** React + Vite → Azure Static Web Apps
- **Backend API:** Azure Functions HTTP triggers
- **Database:** Azure Cosmos DB Serverless (8 containers)
- **Queuing:** Azure Service Bus (alert-queue with DLQ + retry)
- **Real-time:** Azure SignalR
- **AI Search:** Azure AI Search (RAG for SOP/CAPA/GMP documents)
- **MCP Servers:** local stdio (CMMS, QMS, Sentinel DB, AI Search)
- **Identity:** Microsoft Entra ID + RBAC (4 roles: Operator, QA Manager, Auditor, IT Admin)
- **CI/CD:** GitHub Actions → deploy.yml
- **IaC:** Bicep (infra/main.bicep + 5 modules)
- **Region:** Sweden Central

---

## 🏆 Final Results

### Overall Score: **81/120 — EXCELLENT** ✅

> "You are all set! Your results look strong and meet the necessary criteria for success."

| Pillar | Score | Rating | Recommended Actions |
|--------|-------|--------|---------------------|
| **Reliability** | 86/200 | MODERATE ⚠️ | 13 |
| **Security** | 64/100 | MODERATE ⚠️ | 22 |
| **Cost Optimization** | 83/100 | EXCELLENT ✅ | 12 |
| **Operational Excellence** | 91/100 | EXCELLENT ✅ | 7 |
| **Performance Efficiency** | 80/101 | EXCELLENT ✅ | 11 |

---

## 📋 Detailed Recommendations

### Reliability (86/200 — MODERATE) — 13 actions

| ID | Recommendation | Priority |
|----|----------------|----------|
| RE:10 | Monitor network traffic | 65 |
| RE:09 | Automate recovery procedures safely | 60 |
| RE:06 | Define units of scale | 55 |
| RE:09 | Ensure availability during outages | 55 |
| RE:03 | Update failure mode analysis periodically | 50 |
| RE:03 | Document failure mode analysis results | 45 |
| RE:05 | Distribute data across geographical regions | 45 |
| RE:05 | Add redundancy to your network | 45 |
| RE:05 | Use the Deployment Stamps design pattern | 45 |
| RE:06 | Understand the time it takes to perform scaling operations | 45 |
| RE:08 | Monitor resulting behavior during chaos experiments | 45 |
| RE:09 | Do regular drills to practice recovery | 40 |
| RE:08 | Test during planned outages | 35 |

### Security (64/100 — MODERATE) — 22 actions

| ID | Recommendation | Priority |
|----|----------------|----------|
| SE:05 | Limit high-privilege accounts; review regularly and decommission when unnecessary | 100 |
| SE:05 | Use conditional access, JIT, and JEA for privileged roles | 95 |
| SE:10 | Review control plane and data plane access patterns periodically for anomalies | 90 |
| SE:08 | Train the team on hardening techniques for the workload's specific services | 90 |
| SE:06 | Enable DDoS protection on virtual networks with public-facing endpoints | 90 |
| SE:06 | Route all ingress and egress traffic through a firewall | 90 |
| SE:08 | Block legacy authentication methods and delegate all authentication to Microsoft Entra ID | 80 |
| SE:07 | Control Key Vault access using Microsoft Entra ID RBAC and network restrictions | 80 |
| SE:06 | Apply NSGs to every subnet to control inbound and outbound traffic | 80 |
| SE:01 | Include role-based security training requirements in the baseline | 80 |
| SE:06 | Use private endpoints for all PaaS services to eliminate public internet exposure | 70 |
| SE:02 | Provide secure coding training for all developers | 70 |
| SE:04 | Use network perimeters (VNets/NSGs/firewalls) to block unauthorized traffic between workload segments | 60 |
| SE:06 | Enable service-level firewall rules on all PaaS resources to restrict access to allowed networks only | 60 |
| SE:07 | Store encryption keys in hardware-protected key store (Azure Key Vault or Managed HSM) with RBAC access control | 60 |
| SE:02 | Remove unused components from development environments to reduce the attack surface | 60 |
| SE:05 | Implement identity lifecycle management with automated onboarding and offboarding | 60 |
| SE:07 | Use SHA-256 or stronger hash algorithms for data integrity checks; do not use MD5 or SHA-1 | 40 |
| SE:07 | Apply double encryption with customer-managed keys where required by compliance | 40 |
| SE:03 | Review and update data classification when new data types or features are added | 40 |
| SE:03 | Apply consistent classification tags to all resources so compliance reports can be generated automatically | 30 |
| SE:09 | Rotate secrets on a regular schedule and maintain the ability to revoke them quickly | 20 |

### Cost Optimization (83/100 — EXCELLENT) — 12 actions

| ID | Recommendation | Priority |
|----|----------------|----------|
| CO:05 | Evaluate and commit to available discounts | 90 |
| CO:05 | Optimize licensing costs | 90 |
| CO:02 | Maintain the cost model | 75 |
| CO:03 | Regularly review cost data with stakeholders | 75 |
| CO:01 | Develop personnel skills in-house | 70 |
| CO:02 | Associate costs with business metrics | 65 |
| CO:08 | Cost optimize the disaster recovery environment | 60 |
| CO:13 | Define targets for personnel time optimization efforts | 55 |
| CO:04 | Configure cost alerts to monitor usage and spending | 50 |
| CO:09 | Set up a regular flow review schedule to align flow spending to priorities | 40 |
| CO:11 | Optimize network traversal | 40 |
| CO:11 | Choose the right operating system | 30 |

### Operational Excellence (91/100 — EXCELLENT) — 7 actions

| ID | Recommendation | Priority |
|----|----------------|----------|
| OE:09 | Perform a return on investment analysis before automating | 70 |
| OE:11 | Have a hotfix plan | 70 |
| OE:11 | Use progressive exposure techniques in deployment | 65 |
| OE:03 | Plan to use small, iterative deployments | 60 |
| OE:08 | Use automation to provide agility and consistency | 60 |
| OE:04 | Evaluate metrics to quantify development effectiveness | 40 |
| OE:08 | Use root cause analysis (RCA) findings to implement improvements | 30 |

### Performance Efficiency (80/101 — EXCELLENT) — 11 actions

| ID | Recommendation | Priority |
|----|----------------|----------|
| PE:05 | Test scaling | 85 |
| PE:06 | Analyze performance testing results | 85 |
| PE:06 | Create performance testing scenarios | 75 |
| PE:10 | Minimize the effects of upgrades on performance | 75 |
| PE:03 | Evaluate cache requirements | 70 |
| PE:05 | Test and optimize the partitioning scheme | 70 |
| PE:06 | Implement a process for continuous performance testing | 70 |
| PE:10 | Minimize the effects of tooling on performance | 70 |
| PE:02 | Forecast demand by using predictive modeling techniques | 65 |
| PE:04 | Monitor network performance data | 65 |
| PE:12 | Automate performance optimization efforts | 65 |

---

## 🎯 Top Priority Action Items (Cross-Pillar)

### Critical/High Priority (Score ≥ 80)

1. **[Security P:100] SE:05** — Implement JIT/JEA access and conditional access policies for privileged roles
2. **[Security P:95] SE:05** — Limit and regularly review high-privilege accounts
3. **[Security P:90] SE:06** — Add VNet integration, firewall, NSGs, and DDoS protection
4. **[Security P:90] SE:10** — Periodic access pattern reviews for anomaly detection
5. **[Security P:90] SE:08** — Team hardening training for specific Azure services
6. **[Security P:90] CO:05** — Evaluate Azure Reserved Instances / Savings Plans
7. **[Performance P:85] PE:05** — Create and run scaling tests
8. **[Performance P:85] PE:06** — Formal performance testing with Azure Load Testing
9. **[Reliability P:65] RE:10** — Network traffic monitoring
10. **[Reliability P:60] RE:09** — Automated recovery procedures

### Key Architecture Gaps Identified

1. **🔴 No VNet/NSGs/Private Endpoints** (SE:06 P:90, P:80, P:70) — All PaaS services exposed publicly; no network perimeter
2. **🔴 No JIT/Conditional Access for privileged roles** (SE:05 P:100, P:95)
3. **🟡 No formal performance/load testing** (PE:05 P:85, PE:06 P:85, P:75, P:70)
4. **🟡 No blue-green/canary deployment** (OE:11 P:70, P:65)
5. **🟡 No multi-region DR** (RE:05 P:45 — Deployment Stamps, geo-distribution)
6. **🟡 Secret rotation not automated** (SE:09 P:20 — rotate on schedule)
7. **🟡 No cost alert thresholds configured** (CO:04 P:50)

---

## 📊 All 61 Questions & Answers

### WAF Configuration (Q1–Q2)

| # | Topic | Selected Answers |
|---|-------|-----------------|
| 1 | Workload type | Core Well-Architected Review |
| 2 | Review pillars | All 5 pillars (Reliability, Security, Cost Opt., Op. Ex., Perf. Eff.) |

### Reliability (Q3–Q12)

| # | Topic | Selected Answers |
|---|-------|-----------------|
| 3 | Keep workload simple | [0,1,2,3,4] Platform functionality, abstract domain logic, offload cross-cutting, essential capabilities |
| 4 | Identify/rate flows | [0,1,2,3,4] Identify flows, business process, business impact, process owner, criticality rating |
| 5 | Failure mode analysis | [0,1,2,3,4,5] Decompose, identify deps, understand characteristics, identify failure modes, mitigation strategies, impact assessment |
| 6 | Define reliability targets | [0,1,2,3,4] Availability targets, recovery targets, health model, healthy/degraded/unhealthy definitions, stakeholder notification |
| 7 | Implement redundancy | [0,1,2,3,4] Stakeholder familiarity, derive requirements, platform compute redundancy, stateless compute, polyglot persistence |
| 8 | Scaling strategy | [0,1,3,5,6,7] Load patterns, ensure all components scalable, align triggers, autoscaling, configure to avoid excess costs, data partitioning |
| 9 | Self-preservation | [0,1,2,3,4,5,6,7] All: cloud design patterns, loose coupling, standards, async, graceful degradation, failure mitigation, retry, logging |
| 10 | Chaos engineering | [0,1,3,4,5] Familiar with concepts, production-like environment, learn from incidents, test early, use FMA for experiments |
| 11 | Disaster recovery | [0,1,2,3,4,5,7,8,9] All except None: prioritize, thresholds, communication protocols, recovery architecture, prep infrastructure, backup, keep plans current, ensure availability, automation |
| 12 | Monitor health | [0,1,2,3,4,5,6] All except None: monitor flows, telemetry familiarity, intentional design, structured logs, alerts, visual health, platform health |

### Security (Q13–Q23)

| # | Topic | Selected Answers |
|---|-------|-----------------|
| 13 | Security baseline | [0,1,2,4,5,6] Documented baseline, regular reviews, incident response in baseline, automated guardrails, CSPM, compliance requirements |
| 14 | Development security | [0,1,2,4,5,6,7,8] Identified requirements, threat modeling, dependency inventory, controlled dev environments, no prod data in dev, asset catalog, security patches, remove unused components |
| 15 | Data classification | [0,1,2] Inventory, aligned to business requirements, architecture matches classification |
| 16 | Network segmentation | [0,1,3,4] Defense in depth, identity as primary perimeter, access controls, resource organization (mgmt groups) |
| 17 | Identity & Access | [0,1,2] All identity types identified, control/data plane segregated, RBAC least privilege |
| 18 | Network security | [0] Only: evaluated all network flows — **GAP: no VNet/NSGs/firewall/private endpoints/DDoS** |
| 19 | Encryption | [0,1,2,4,5,8] Platform encryption, keys stored separately, industry-standard algorithms, TLS 1.2+, cert revocation, identity-based key access |
| 20 | Hardening | [0,2,3,4,5] Asset inventory, documented requirements, deny-by-default access, no legacy protocols, modern auth |
| 21 | Secrets management | [0,1,2,3,5,6] Separate per-env secrets, Key Vault, managed identity distribution, automated scanning, rotation without downtime, RBAC |
| 22 | Security monitoring | [0,1,2,4,5,6] Cloud-native monitoring, structured logging, activity logs, centralized threat detection, drift monitoring, automated threat detection |
| 23 | Security testing | [0,5] Security in DevOps pipelines, manual security testing + scanning tools |

### Cost Optimization (Q24–Q37)

| # | Topic | Selected Answers |
|---|-------|-----------------|
| 24 | Financial culture | [0,1,3] Communicate expectations, transparent budgets, continuous improvement culture |
| 25 | Cost model | [0,1,3] Workload estimates, cost drivers identified, budget set |
| 26 | Cost reporting | [0,1,2,3,5] Data collection, grouped, reports generated, resource owners assigned, cost alerts |
| 27 | Cost guardrails | [0,1,3,4] Governance policies, release gates, IaC standardized deployments, access controls |
| 28 | Pricing & licensing | [0,1,3] Understand costs, right billing model, build-or-buy evaluation |
| 29 | Billing increments | [0,1,2,3,4] All: know factors, map usage, POC validation, modify services, modify usage |
| 30 | Resource efficiency | [0,1,2,3] Optimize app features, platform features, cost-optimize resources, avoid unoptimized components |
| 31 | Environment cost | [0,1,3] Understand env value, optimize production, optimize preproduction |
| 32 | Flow optimization | [0,1,2,3,4] Inventory flows, prioritize by value, optimize independent flows, separate dissimilar, combine similar |
| 33 | Data management | [0,1,2,3,4,5,6] All: inventory, prioritize, lifecycle management, cost-optimize storage, replication config, optimize backups, limit data captured |
| 34 | Code efficiency | [0,1,2,3,6,7] Instrumented, hot paths optimized, concurrent processing, SDKs optimized, data access, architecture evaluation |
| 35 | Scaling | [0,1,2,3,4] Scale model analysis, reduce demand, autoscaling, offload demand, spending limits |
| 36 | Personnel efficiency | [1,2,3,4,5] Dev time, collaboration, processes, operational tasks, skills |
| 37 | Consolidation | [0,1,2,3] Internal consolidation, understand process, offload to external teams, centralized resources |

### Operational Excellence (Q38–Q48)

| # | Topic | Selected Answers |
|---|-------|-----------------|
| 38 | Team culture | [0,1,2,3,4,5] Mutual respect, end-to-end responsibility, enablement teams, cross-functional, integrated requirements, regular reviews |
| 39 | Operating procedures | [0,1,2,3,4,5,6,7] All except None: templates, guidelines, checklists, incident response, industry practices, shift-left, compliance, open-source |
| 40 | Development planning | [0,1,2,3,4,5,6] All except None: collaborative, proven processes, iterative, communication, user stories, acceptance criteria, retrospectives |
| 41 | Development standards | [0,1,3,4,5,6,7] Industry tools, style guide, unit testing, tech debt, versioning, branching, naming/tagging |
| 42 | IaC | [0,1,2,3,4,5,6] All except None: declarative Bicep, purposeful choice, API lifecycle, multi-env, modules, layers, code-managed |
| 43 | Deployment strategy | [0,1,2,3,4,5,6] All except None: all through pipelines, immutable infra, single code base, standard production, separate pipelines, shift-left, quality gates |
| 44 | Observability | [0,1,2,3,4,5,6,7] All except None: telemetry, retention, env separation, holistic+flow views, structured events, platform services, visualization, alerting |
| 45 | Incident response | [0,1,2,3,4,5,6,8,9] All except 7/None: plan, resources, containment, monitoring, diagnostics, dashboard, audit, RCA improvements, automation |
| 46 | Automation | [0,2,3] Broad consideration, self-service, appropriate tools |
| 47 | Automation design | [0,1,2,3,4,5] All except None: automation-central, bootstrapping, desired state, control plane, managed identity auth, platform tools |
| 48 | Safe deployment | [0,2,4,5] Small incremental changes, health signals for go/no-go, reliable data changes, all prod through pipeline |

### Performance Efficiency (Q49–Q61)

| # | Topic | Selected Answers |
|---|-------|-----------------|
| 49 | Performance requirements | [0,1,2,3,4] Understand requirements, identify metrics, set targets, document targets, customer feedback |
| 50 | Capacity planning | [0,2,3,4] Gather data, align with objectives, resource requirements, understand quotas |
| 51 | Service selection | [0,1,2,3,4,5,6,7] All except None: performance-based selection, platform features, latency-aware infra, networking, compute, load balancing, data stores, caching |
| 52 | Performance monitoring | [0,1,2,3,4,6] Central storage, per-env separate, retention policies, code instrumented, all resources, database performance |
| 53 | Scaling | [0,1,2,3,4,5,7] Scaling strategy, scalable infra, scalable app, understand limits, metric-based scaling, autoscaling with guardrails, partitioning strategy |
| 54 | Performance testing | [0,1,2] Acceptance criteria defined, identified test types, decided on toolset |
| 55 | Code optimization | [0,1,2,3,4] All except None: code logic, memory, concurrency (asyncio/Durable), connection pooling, infrastructure |
| 56 | Data optimization | [0,1,2,3,4,5,6,7,8] All except None: profiling, monitoring, partitioning, query tuning, indexes, compression, caching, consistency level, data proximity |
| 57 | Critical flows | *(Q not tracked — scored during session)* |
| 58 | Operational tasks | [0,1,4,5] Identify overhead, optimize deployments, DB operational tasks, monitoring level |
| 59 | Live performance issues | [0,1,2,3] All except None: prepared, triage plan, methods to identify/resolve, feedback loop |
| 60 | Continuous optimization | [0,1,2,4] Culture of optimization, evaluate new platform features, address deteriorating components, tech debt |

---

## 🚀 Recommended Next Steps (Priority Order)

### Immediate (Critical Security Gaps)
1. **Add VNet integration** for Azure Functions and Service Bus with private endpoints
2. **Enable NSGs** on all subnets; restrict outbound to specific service tags only
3. **Implement DDoS Standard** protection on the public-facing Static Web App
4. **Configure Conditional Access** policies: MFA for all Entra ID users; JIT access for privileged roles
5. **Automate secret rotation** via Key Vault rotation policies and Function triggers

### Short-Term (Performance & Reliability)
6. **Azure Load Testing** — create perf test scenarios for normal and peak load
7. **Blue-green / canary deployment** slots for Azure Functions (via deployment slots)
8. **Document chaos experiments** with Azure Chaos Studio; run initial tests
9. **Automate recovery runbook** steps via Logic Apps or Durable Functions
10. **Configure cost alerts** in Azure Cost Management for each pillar budget threshold

### Medium-Term (Architecture Improvements)
11. **Multi-region DR plan** — geo-redundant Cosmos DB + Azure AI Search replica
12. **Deployment Stamps pattern** — package all resources per region for DR
13. **Customer-managed keys (CMK)** via Key Vault for Cosmos DB, AI Search if GMP requires
14. **Role-based security training** program for the team
15. **Azure DevOps / ADO work items** — import WAR CSV for tracked action items

---

*Assessment completed: April 22, 2026*  
*Session URL: https://learn.microsoft.com/en-us/assessments/azure-architecture-review/sessions/e2c98b12-7804-449f-ac6a-e29a797758b8?mode=guidance*

