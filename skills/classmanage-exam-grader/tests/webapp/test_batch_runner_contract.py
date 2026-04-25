from webapp import main
from webapp.services import batch_runner


def test_main_uses_batch_runner_module_for_batch_orchestration() -> None:
    assert main._start_batch_processing is batch_runner.start_batch_processing
    assert main._process_batch is batch_runner.process_batch
