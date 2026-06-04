# 콘텐츠 소스 목록 — AI Pulse

> 기준 버전: PRD v3.0

## 도입 단계

| 단계 | 소스 그룹 | 시기 | 상태 |
|---|---|---|---|
| Phase 1 (MVP) | 그룹 A 전체 + 그룹 B-1 + 그룹 C-1 일부 + 그룹 D-1 일부 | MVP | ✅ 완료 |
| Phase 2 | 그룹 B-2, B-3 + 그룹 C-2 | 앱 출시 후 | ✅ 완료 (S6) |
| Phase 3 | 그룹 D-2 (이메일 IMAP) | 고도화 단계 | ✅ 완료 (S6) |

---

## 그룹 A — 뉴스 RSS (주 카드 타입: NEWS)

| 소스 | 언어 | 수집 방식 | 주요 카테고리 | Phase |
|---|---|---|---|---|
| TechCrunch AI | EN | RSS | 일반 | 1 |
| The Verge AI | EN | RSS | 일반 | 1 |
| MIT Technology Review AI | EN | RSS | 일반 | 1 |
| arXiv (cs.AI, cs.CL) | EN | RSS | 프로그래밍 | 1 |
| Hacker News (AI 태그) | EN | HN API | 프로그래밍/일반 | 1 |
| AI타임스 | KO | RSS | 일반 | 1 |
| 인공지능신문 | KO | 웹 크롤링 | 일반 | 1 |
| GeekNews | KO | RSS | 프로그래밍 | 1 |
| 요즘IT | KO | RSS | 프로그래밍/디자인 | 1 |

---

## 그룹 B — GitHub (주 카드 타입: TECHNIQUE)

### B-1. Releases API — 핵심 프레임워크 (Phase 1)

| 리포지토리 | 카테고리 | 설명 |
|---|---|---|
| `langchain-ai/langchain` | 프로그래밍 | LLM 앱 프레임워크 |
| `run-llama/llama_index` | 프로그래밍 | RAG 프레임워크 |
| `microsoft/autogen` | 프로그래밍 | Multi-agent 프레임워크 |
| `joaomdmoura/crewAI` | 프로그래밍 | Agent team 프레임워크 |
| `stanfordnlp/dspy` | 프로그래밍 | 프롬프트 최적화 |
| `modelcontextprotocol/servers` | 프로그래밍 | MCP 공식 서버 모음 |
| `vercel/ai` | 프로그래밍 | Vercel AI SDK |
| `pydantic/pydantic-ai` | 프로그래밍 | Type-safe agent 프레임워크 |
| `huggingface/transformers` | 프로그래밍 | 모델 라이브러리 |

**수집 조건**: CHANGELOG 본문 300자 미만이면 단순 버전업으로 제외

### B-2. Trending Repos — GitHub Search API (Phase 2) ✅

| 토픽 | 최소 별 수 | 수집 주기 | 구현 |
|---|---|---|---|
| `topic:llm` | 100개 | 일 1회 (KST 00시) | `group_b2.py` |
| `topic:llm-agents` | 50개 | 일 1회 | `group_b2.py` |
| `topic:rag` | 50개 | 일 1회 | `group_b2.py` |
| `topic:mcp` | 30개 | 일 1회 | `group_b2.py` |
| `topic:ai-coding` | 50개 | 일 1회 | `group_b2.py` |

**어댑터**: `pipeline/adapters/github_trending.py` (GitHubTrendingAdapter)

### B-3. Awesome 리스트 README 변경 감지 (Phase 2) ✅

| 리스트 | 추적 방식 | 구현 |
|---|---|---|
| `Hannibal046/Awesome-LLM` | README.md commit diff 분석 | `group_b3.py` |
| `e2b-dev/awesome-ai-agents` | README.md commit diff 분석 | `group_b3.py` |
| `aishwaryanr/awesome-generative-ai-guide` | README.md commit diff 분석 | `group_b3.py` |
| `punkpeye/awesome-mcp-servers` | README.md commit diff 분석 | `group_b3.py` |

---

## 그룹 C — 엔지니어링 블로그 RSS (주 카드 타입: TECHNIQUE)

### C-1. 기업 엔지니어링 블로그 (Phase 1)

| 소스 | 카테고리 | RSS |
|---|---|---|
| Anthropic Engineering | 프로그래밍 | ✅ |
| OpenAI Blog | 프로그래밍/일반 | ✅ |
| Vercel AI Blog | 프로그래밍 | ✅ |
| LangChain Blog | 프로그래밍 | ✅ |
| LlamaIndex Blog | 프로그래밍 | ✅ |
| Hugging Face Blog | 프로그래밍 | ✅ |
| Replit Blog | 프로그래밍 | ✅ |
| Google DeepMind Blog | 프로그래밍/일반 | ✅ |

### C-2. 개인 엔지니어 블로그 (Phase 2) ✅

| 블로거 | RSS | 강점 분야 |
|---|---|---|
| Simon Willison | `simonwillison.net/atom/everything/` | AI 엔지니어링 전반, 실험 기록 |
| Eugene Yan | `eugeneyan.com/feed.xml` | LLM 시스템 설계, 평가 |
| Lilian Weng | `lilianweng.github.io/index.xml` | 딥러닝 이론, 에이전트 |
| Chip Huyen | `huyenchip.com/feed.xml` | ML 시스템, LLMOps |
| Hamel Husain | `hamel.dev/feed.xml` | LLM 평가, RAG 패턴 |

**구현**: `pipeline/sources/group_c2.py`

### C-3. OpenAI Cookbook (Phase 2)

| 리포지토리 | 추적 방식 |
|---|---|
| `openai/openai-cookbook` | Commits API로 신규 .ipynb 감지 |

---

## 그룹 D — 뉴스레터 (주 카드 타입: TECHNIQUE)

### D-1. Substack RSS (Phase 1)

| 뉴스레터 | 주기 |
|---|---|
| Latent Space | 주 2~3회 |
| Import AI | 주 1회 |
| The Batch (DeepLearning.AI) | 주 1회 |
| Ahead of AI (Sebastian Raschka) | 격주 |

### D-2. 이메일 IMAP (Phase 3) ✅

| 뉴스레터 | 발신자 이메일 | 수집 방식 | 주기 |
|---|---|---|---|
| TLDR AI | `dan@tldrnewsletter.com` | IMAP 폴링 | 일 1회 |
| Ben's Bites | `bens-bites@bensbites.beehiiv.com` | IMAP 폴링 | 일 1회 |
| The Rundown AI | `therundownai@mail.beehiiv.com` | IMAP 폴링 | 일 1회 |
| AI Engineer Weekly | `contact@aiweekly.co` | IMAP 폴링 | 주 1회 |

**인프라**: 전용 Gmail 계정 + 2FA + 앱 비밀번호 + `imap-tools` 라이브러리
**어댑터**: `pipeline/adapters/imap.py` (IMAPAdapter)
**구현**: `pipeline/sources/group_d2.py`
**환경변수**: `IMAP_HOST`, `IMAP_USER`, `IMAP_PASSWORD`, `IMAP_MAILBOX`

---

## GitHub API 운영 주의사항

| 항목 | 내용 |
|---|---|
| Rate Limit | 인증 토큰 기준 시간당 5,000건 |
| 배치당 예상 사용량 | 50~100건 (여유 있음) |
| 403 응답 처리 | 다음 배치로 자동 연기 |
| 404 응답 처리 | 리포 삭제로 간주, source_health 비활성화 |
| 인증 방식 | Fine-grained Personal Access Token (환경 변수) |
