---
title: "Khảo sát framework Agentic RAG, GraphRAG và Legal RAG cho ALQAC 2026"
date: 2026-07-16T22:25:00+07:00
status: completed
scope: [rag, graphrag, knowledge-graph, legal-rag, alqac]
---

# Khảo sát framework Agentic RAG, GraphRAG và Legal RAG cho ALQAC 2026

## Mục lục

1. [Kết luận nhanh](#kết-luận-nhanh)
2. [Phạm vi và cách khảo sát](#phạm-vi-và-cách-khảo-sát)
3. [Bốn loại GraphRAG thường bị gọi chung](#bốn-loại-graphrag-thường-bị-gọi-chung)
4. [So sánh framework phổ biến](#so-sánh-framework-phổ-biến)
5. [Framework và nghiên cứu riêng cho luật](#framework-và-nghiên-cứu-riêng-cho-luật)
6. [Tín hiệu từ cộng đồng](#tín-hiệu-từ-cộng-đồng)
7. [Khuyến nghị cho ALQAC](#khuyến-nghị-cho-alqac)
8. [Lộ trình thử nghiệm](#lộ-trình-thử-nghiệm)
9. [Rủi ro và câu hỏi chưa chốt](#rủi-ro-và-câu-hỏi-chưa-chốt)
10. [Nguồn chính](#nguồn-chính)

## Kết luận nhanh

ALQAC đúng là bài toán **Agentic RAG hai nguồn**: agent truy vấn Case Retrieval API để tìm phán quyết/bằng chứng vụ án, đồng thời truy vấn corpus luật local để tìm căn cứ pháp lý. Tuy nhiên chỉ nguồn luật tĩnh thực sự phù hợp để xây Knowledge Graph đầy đủ. Case API là corpus từ xa, bị giới hạn lượt gọi và chỉ trả chunk theo query; ta không có toàn bộ dữ liệu để lập graph toàn cục.

Khuyến nghị:

1. Giữ agent loop nhỏ, có ba tool `SEARCH_CASE`, `SEARCH_LAW`, `FINISH`; không cần framework nặng ở vòng đầu.
2. Nâng law retrieval thành **hybrid legal retrieval**: exact citation + BM25 + dense retrieval + reranker, sau đó mở rộng graph tối đa 1 hop.
3. Xây legal graph có schema rõ bằng rule trước: `Law → Article → Clause`, cùng các cạnh `CITES`, `AMENDS`, `REPEALS`, `REPLACES`, `GUIDES`, `DEFINES` nếu corpus có dữ liệu.
4. Dùng ý tưởng của **SBV-LawGraph** cho retrieval luật Việt Nam và **LegalGraphRAG** cho vai trò Researcher → Auditor → Adjudicator. Không bê nguyên code/model của hai hệ thống.
5. Nếu cần framework: thử **LlamaIndex PropertyGraphIndex** trước; dùng **Neo4j GraphRAG** khi thật sự cần Cypher, lưu graph lâu dài hoặc trực quan hóa. LightRAG là baseline nghiên cứu đáng thử; Microsoft GraphRAG không hợp bài hiện tại.

## Phạm vi và cách khảo sát

- Thời điểm khảo sát: 2026-07-16.
- Tài liệu ưu tiên: repo/docs chính thức, paper gốc, ACL/CEUR; cộng đồng chỉ dùng làm tín hiệu thực hành, không coi là benchmark.
- Khoảng thời gian chính: 2024–2026.
- Tiêu chí: độ phù hợp với hai nguồn ALQAC, khả năng chạy open-weight/local, audit citation, chi phí indexing, mức độ trưởng thành, khả năng kiểm soát agent và độ phức tạp vận hành.
- Ngoài phạm vi: chọn model/embedding cuối cùng, benchmark GPU, triển khai production và gọi thêm Case Retrieval API.

## Bốn loại GraphRAG thường bị gọi chung

### 1. Graph từ entity tự trích xuất

LLM đọc tài liệu, trích entity/relationship, tạo community và summary. Microsoft GraphRAG là đại diện. Cách này mạnh với câu hỏi tổng quan trên corpus lớn nhưng indexing tốn LLM, graph có thể sai nếu extraction sai.

### 2. Property Graph có schema

Người thiết kế định nghĩa loại node/cạnh; retriever dùng vector, keyword, graph traversal hoặc Text-to-Cypher. LlamaIndex PropertyGraphIndex và Neo4j GraphRAG thuộc nhóm này. Đây là nhóm hợp với luật vì cấu trúc Điều/Khoản/viện dẫn có thể xác định rõ.

### 3. Graph để multi-hop retrieval

Entity/link được dùng cùng Personalized PageRank hoặc graph model để tìm đường suy luận nhiều bước. HippoRAG và GFM-RAG thuộc nhóm này. Phù hợp nghiên cứu multi-hop nhưng có thêm model, indexing và hạ tầng.

### 4. Legal Knowledge Graph

Graph biểu diễn cấu trúc và hiệu lực pháp lý: văn bản chứa Điều nào, Điều nào viện dẫn/sửa đổi/bãi bỏ/hướng dẫn Điều nào. Đây không đơn thuần là entity graph. Với ALQAC, loại này có giá trị cao nhất vì output yêu cầu `law_id + aid` và cần citation kiểm chứng được.

## So sánh framework phổ biến

| Framework | Điểm mạnh | Điểm yếu | Hợp ALQAC |
|---|---|---|---|
| [Microsoft GraphRAG](https://github.com/microsoft/graphrag) | Local/global/DRIFT query; pipeline graph/community rõ; cộng đồng lớn | Repo tự cảnh báo indexing đắt, là demonstration chứ không phải sản phẩm được hỗ trợ; config có breaking changes | **Thấp–trung bình**. Quá nặng, tối ưu cho khám phá corpus/tổng hợp toàn cục hơn là trả đúng Article ID |
| [LightRAG](https://github.com/HKUDS/LightRAG) | Dự án rất active; local/global/hybrid/mix; nhiều storage backend, citation, reranker, tracing | Entity extraction và graph tự sinh khó audit pháp lý; surface area lớn, thay đổi nhanh | **Trung bình**. Tốt làm baseline GraphRAG, không nên là source of truth cho citation |
| [LlamaIndex PropertyGraphIndex](https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/) | Retriever composable; hỗ trợ property graph/schema; có thể phối hợp vector và graph; tích hợp nhiều graph store | Dependency lớn, API thay đổi theo hệ sinh thái; vẫn phải tự định nghĩa ontology/eval | **Cao cho prototype** nếu muốn framework |
| [Neo4j GraphRAG Python](https://github.com/neo4j/neo4j-graphrag-python) | Package chính thức; KG builder có schema; vector/hybrid/graph retrieval; lưu provenance và query bằng Cypher tốt | Phải vận hành Neo4j; một phần KG pipeline còn dưới namespace `experimental`; quá tay nếu corpus nhỏ | **Cao khi cần DB/UI**, trung bình cho MVP |
| LangGraph + retriever tự viết | State machine, tool loop, retry/stop/audit dễ biểu diễn | Không tự cung cấp KG retrieval; vẫn phải ghép retriever/graph store | **Cao cho orchestration**, nhưng custom loop hiện tại còn đơn giản hơn |
| [HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | Multi-hop qua KG + Personalized PageRank; phù hợp câu hỏi cần nối nhiều tài liệu | Thiên nghiên cứu, indexing/model phụ nặng hơn; graph extraction vẫn là nút rủi ro | **Trung bình** cho ablation, chưa nên làm nền chính |
| [GFM-RAG](https://github.com/RManLuo/gfm-rag) | Có graph retriever học được, hỗ trợ bring-your-own-graph và agent multi-step | Rất mới; yêu cầu Python 3.12/CUDA 12; thêm pipeline training/model | **Thấp ở MVP**, đáng theo dõi nghiên cứu |

### Nhận xét thẳng

- “Nhiều sao” không đồng nghĩa phù hợp pháp lý. Framework tự trích entity dễ tạo graph nhìn đẹp nhưng sai quan hệ pháp luật.
- Với corpus luật nhỏ/vừa, adjacency JSON hoặc NetworkX đã đủ. Neo4j chỉ có lợi khi cần query phức tạp, versioning, nhiều quan hệ hoặc quan sát graph.
- Agent orchestration và retrieval engine là hai lớp khác nhau. LangGraph không thay thế BM25/dense/KG; Microsoft GraphRAG cũng không tự giải quyết quy tắc nộp evidence của ALQAC.

## Framework và nghiên cứu riêng cho luật

### LegalGraphRAG — tham chiếu agent phù hợp nhất

[LegalGraphRAG](https://github.com/XMUDeepLIT/LegalGraphRAG) là code chính thức của paper ACL 2026. Hệ thống dùng hierarchical legal graph và ba vai trò:

1. **Researcher** tìm bằng chứng ứng viên.
2. **Auditor** kiểm tra bằng chứng với nguồn gốc.
3. **Adjudicator** tổng hợp bằng chứng đã xác minh để đưa ra phán quyết.

Ý tưởng này rất sát ALQAC: tách retrieval khỏi verification, không cho model kết luận trực tiếp từ context chưa audit. Điểm yếu: repo/paper rất mới; cần xem như kiến trúc tham khảo, chưa phải dependency ổn định.

### SBV-LawGraph — tham chiếu retrieval luật Việt Nam phù hợp nhất

[SBV-LawGraph](https://lexuanbach.github.io/publication/ACIIDS2026a.pdf) của HCMUT/VNU-HCM dùng hai nhánh:

- Sparse + dense retrieval, hợp nhất bằng RRF rồi rerank.
- Legal Knowledge Graph mở rộng 1 hop cho quan hệ sửa đổi, bãi bỏ, thay thế và hướng dẫn.

Paper báo cáo trên dữ liệu ALQAC 2025 rằng R@1 tăng từ 0.57 của BM25 lên 0.69 và R@2 từ 0.65 lên 0.73. Đây là kết quả của chính paper, chưa phải reproduction độc lập. Kiến trúc rất đáng áp dụng, nhưng bản paper dùng Qdrant, Neo4j, model embedding/reranker và `gpt-oss-120b` để trích graph; không thể bê nguyên vào ALQAC 2026 nếu giới hạn model dưới 10B áp dụng cho toàn pipeline.

### LegalBench-RAG và Legal RAG Bench — benchmark, không phải framework

- [LegalBench-RAG](https://github.com/zeroentropy-cc/legalbenchrag) có 6.858 query-answer pairs, tập trung đánh giá retrieval ở mức đoạn nhỏ, chính xác và có thể citation.
- [Legal RAG Bench](https://arxiv.org/abs/2603.01710) đánh giá end-to-end; kết quả paper cho rằng retrieval là yếu tố chi phối nhiều hơn generator trong legal RAG.
- [LRAGE](https://github.com/hoorangyee/LRAGE) là toolkit đánh giá RAG pháp lý trên nhiều benchmark.

Bài học cho ALQAC: phải tách metric retrieval khỏi outcome. Ít nhất cần `Recall@k`, `MRR`, citation validity, context precision và per-label outcome; không chỉ nhìn Final Score.

### GraphRAG cho luật nói chung

[Nghiên cứu PROPOR 2026](https://aclanthology.org/2026.propor-1.1/) mô hình hóa Document/Article/Paragraph/Item và tái dựng đường context từ root đến leaf. [Graph RAG for Legal Norms](https://arxiv.org/abs/2505.00039) nhấn mạnh hierarchy, cross-reference và phiên bản theo thời gian. Cả hai củng cố lựa chọn “schema pháp lý trước, entity graph sau”.

## Tín hiệu từ cộng đồng

Đây là kinh nghiệm không kiểm soát, chỉ dùng để định hướng thử nghiệm:

- Nhiều người triển khai nhấn mạnh chunking và metadata quan trọng hơn đổi framework; tài liệu luật nên giữ số Điều/Khoản và parent context. [Thảo luận LocalLLaMA](https://www.reddit.com/r/LocalLLaMA/comments/1pzd0s1/best_rag_framework_for_largescale_document_search/)
- Một pipeline luật thực tế chia retrieval theo nguồn, dùng sparse + dense, RRF, rerank theo cấp tòa/thời gian và hard-validate stable chunk ID. [Thảo luận CDRAG](https://www.reddit.com/r/Rag/comments/1svgyq4/cdrag_rag_with_llmguided_document_retrieval/)
- Cộng đồng pháp lý cảnh báo semantic relevance không đủ: thẩm quyền, cấp văn bản, hiệu lực, jurisdiction và việc án bị đảo phải là metadata. [Thảo luận authority-aware retrieval](https://www.reddit.com/r/Rag/comments/1th5tbb/legal_rag_remains_unsolved_because_it_needs/)
- Neo4j/GraphRAG thường tốn công ở entity resolution và ontology hơn demo thể hiện; graph tự sinh không tự động bảo đảm retrieval tốt. [Thảo luận Neo4j LLM Graph Builder](https://www.reddit.com/r/Rag/comments/1i1980p/neo4js_llm_graph_builder_seems_useless/)

Điểm đồng thuận hữu ích: hybrid retrieval + reranker + citation validation nên làm trước full GraphRAG.

## Khuyến nghị cho ALQAC

### Kiến trúc đích

```text
PrivateCase(case_id, case_query)
        |
        v
Case Researcher Agent
  |-- SEARCH_CASE(query) -> exact JSON cache/API -> candidate chunks
  |-- đánh giá đủ/thiếu -> query tiếp hoặc dừng
        |
        v
Evidence Auditor
  |-- nguồn có phải lời tòa không?
  |-- chunk_id có thật trong raw response không?
        |
        +--------------------------+
        |                          |
        v                          v
Outcome Adjudicator         Legal Query Builder
                                   |
                                   v
                      exact citation + BM25 + dense
                                   |
                                   v
                         RRF/rerank top candidates
                                   |
                                   v
                       Legal KG expansion tối đa 1 hop
                                   |
                                   v
FINISH(verdict_label, case_evidence, law_evidence)
        |
        v
Strict validator
```

### Graph nên đặt ở đâu?

**Law corpus:** graph lâu dài, deterministic và có schema.

```text
(Law)-[:CONTAINS]->(Article)-[:CONTAINS]->(Clause)
(Article)-[:CITES]->(Article)
(Document)-[:AMENDS|REPEALS|REPLACES|GUIDES]->(Document|Article)
(Article)-[:DEFINES]->(LegalTerm)
```

**Case retrieval:** không cố xây global KG vì ta không có corpus gốc. Chỉ tạo graph tạm theo từng vụ để audit:

```text
(Query)-[:RETURNED]->(Chunk)-[:SUPPORTS|CONTRADICTS]->(Claim)
(Claim)-[:SUPPORTS_LABEL]->(Outcome)
```

Graph tạm này có thể là JSON trace, không cần Neo4j.

### Chọn công nghệ

**Khuyến nghị MVP:** custom Python state machine + law graph dạng adjacency JSON/dict. Lý do: package hiện chỉ dùng standard library, corpus luật đã local, output cần ID chính xác và deadline thi ưu tiên audit hơn abstraction.

**Prototype framework:** LlamaIndex PropertyGraphIndex, vì dễ ghép vector + property graph và không buộc Neo4j ngay từ đầu.

**Khi cần scale/quan sát:** Neo4j GraphRAG, nếu số node/edge lớn, cần Cypher, temporal versioning hoặc UI graph.

**Baseline nghiên cứu:** LightRAG để so retrieval, không dùng entity graph của nó làm citation source nếu chưa audit.

**Không ưu tiên:** Microsoft GraphRAG, HippoRAG, GFM-RAG ở vòng kế tiếp; lợi ích chưa tương xứng indexing/model/hạ tầng.

## Lộ trình thử nghiệm

### P0 — không cần API mới

1. Xây evaluation riêng cho outcome, case chunk retrieval và law retrieval.
2. Parse law corpus thành node `Law/Article`; tạo cạnh hierarchy và direct citation bằng rule/regex.
3. Thêm dense retriever nhỏ + BM25, hợp nhất RRF; rerank top 10 xuống top 2–3.
4. Chạy agent/auditor trên cache case hiện có; không thay đổi submission.
5. Ablation: BM25 → hybrid → hybrid+rerank → hybrid+rerank+1-hop graph.

### P1 — khi có model open-weight hợp lệ

1. Dùng model làm query planner và adjudicator, structured JSON bắt buộc.
2. Auditor kiểm từng claim với chunk/citation, không chỉ hỏi model “có đúng không”.
3. So custom loop với LlamaIndex prototype trên cùng cache và metric.
4. Chỉ giữ graph edge do LLM trích nếu qua rule hoặc audit thủ công mẫu.

### P2 — khi có thêm Case API budget

1. Freeze prompt/query policy trước khi gọi.
2. Test pilot vài case, đo source hit và marginal gain/query.
3. Cho agent tối đa số query luật thi cho phép; dừng sớm khi evidence đủ.
4. Mọi request tiếp tục đi qua exact cache và intent ledger.

## Rủi ro và câu hỏi chưa chốt

### Rủi ro

- LLM-built KG sai quan hệ pháp lý nhưng nhìn hợp lý.
- Dense retriever kéo đoạn gần nghĩa nhưng sai Điều/phiên bản/hiệu lực.
- Graph expansion làm tăng recall nhưng giảm precision và tốn context.
- Framework thay đổi nhanh gây mất thời gian migration.
- Dùng model/indexing model vượt giới hạn cuộc thi dù generator hợp lệ.
- Public label tuning tạo kết quả đẹp nhưng không tổng quát sang Private Test.

### Câu hỏi chưa chốt

1. Giới hạn model dưới 10B áp dụng chỉ generator hay cả embedding/reranker/KG extraction?
2. Corpus luật có metadata sửa đổi/bãi bỏ/hiệu lực hay phải suy từ text?
3. Public labels được phép dùng để chọn prompt/hyperparameter ở mức nào?
4. Ban tổ chức có cấp/reset Case Retrieval API budget cho Private phase không?
5. Case API search trên một corpus chung hay corpus bị giới hạn theo `case_id`?

## Nguồn chính

### Official docs/GitHub

- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [Microsoft GraphRAG documentation](https://microsoft.github.io/graphrag/)
- [LightRAG](https://github.com/HKUDS/LightRAG)
- [LlamaIndex Property Graph Index](https://developers.llamaindex.ai/python/framework/module_guides/indexing/lpg_index_guide/)
- [Neo4j GraphRAG Python](https://github.com/neo4j/neo4j-graphrag-python)
- [Neo4j GraphRAG documentation](https://neo4j.com/docs/neo4j-graphrag-python/current/)
- [HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG)
- [GFM-RAG](https://github.com/RManLuo/gfm-rag)
- [LegalGraphRAG](https://github.com/XMUDeepLIT/LegalGraphRAG)
- [LegalBench-RAG](https://github.com/zeroentropy-cc/legalbenchrag)
- [LRAGE](https://github.com/hoorangyee/LRAGE)

### Papers

- [LegalGraphRAG, ACL 2026](https://arxiv.org/abs/2605.28120)
- [SBV-LawGraph, ACIIDS 2026](https://lexuanbach.github.io/publication/ACIIDS2026a.pdf)
- [Benchmarking KG-based RAG Systems on Legal Documents, 2025](https://ceur-ws.org/Vol-4079/paper6.pdf)
- [LegalBench-RAG, 2024](https://arxiv.org/abs/2408.10343)
- [Legal RAG Bench, 2026](https://arxiv.org/abs/2603.01710)
- [Graph RAG for Legal Norms, 2025](https://arxiv.org/abs/2505.00039)
- [GraphRAG for Portuguese Legal Documents, PROPOR 2026](https://aclanthology.org/2026.propor-1.1/)
