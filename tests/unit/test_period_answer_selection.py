"""A higher model score or supplied confidence cannot override the requested year."""
from types import SimpleNamespace
from fastapi.testclient import TestClient
from hybrid_search.api import create_app
from hybrid_search.models.search import SearchResult
from hybrid_search.retrieval.reranker import NeuralReranker

QUERY = "What were NVIDIA's basic weighted average shares in fiscal 2025?"


def result(year, value):
    return SearchResult(
        chunk_id=str(year), document_id=str(year), rank=1, score=9.0,
        text=f'[NVIDIA Corporation (NVDA) | 10-K FY{year}]\n\nBasic weighted average shares (Year Ended): Jan 26, {year} = {value}. Unit: millions of shares.',
        company='NVIDIA Corporation', ticker='NVDA', document_type='10-K',
        filing_date=f'{year}-02-01', fiscal_period=f'FY{year}', section='Item 8',
        retrieval_method='rerank', exact_answer=f'FY{year}: {value}', answer_confidence=0.99,
    )


def test_rerank_wrong_year_high_score_cannot_hide_matching_year():
    reranker = NeuralReranker()
    reranker.max_passage_tokens = 0
    reranker._model = SimpleNamespace(rerank=lambda *args, **kwargs: [9.0, 1.0])
    chosen, = reranker.rerank(QUERY, [result(2023, '2,487'), result(2025, '24,555')], top_k=1)
    assert chosen.chunk_id == '2025'
    assert chosen.exact_answer.endswith('24,555 million shares')


def test_api_rechecks_precomputed_high_confidence_answer_against_columns():
    engine = SimpleNamespace(search=lambda **kwargs: [result(2023,'2,487'), result(2025,'24,555')])
    client = TestClient(create_app(engine=engine))
    response = client.post('/api/search', json={'query': QUERY, 'method': 'rerank', 'k': 5})
    assert response.status_code == 200, response.text
    answer = response.json()['direct_answer']
    assert answer['exact_answer'].endswith('24,555 million shares')
    assert 'FY2025' in answer['source']


def test_api_abstains_if_all_columns_are_wrong_year():
    engine = SimpleNamespace(search=lambda **kwargs: [result(2023,'2,487')])
    client = TestClient(create_app(engine=engine))
    response = client.post('/api/search', json={'query': QUERY, 'method': 'rerank', 'k': 5})
    assert response.status_code == 200, response.text
    assert response.json()['direct_answer'] is None
