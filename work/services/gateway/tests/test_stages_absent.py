"""New local feature absence probes; not a claim that missing imports test security."""

def test_s03_default_off_authenticated_entrypoint_exists():
    from work_service import create_work_app
    assert callable(create_work_app)


def test_s04_incremental_bounded_stream_entrypoint_exists():
    from sse_protocol import SSEDecoder
    assert SSEDecoder().feed(b': heartbeat\n\n') == []


def test_s05_actual_owned_qa_runner_exists():
    from qa_workflow import run_owned_qa
    assert callable(run_owned_qa)
