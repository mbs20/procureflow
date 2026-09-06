from procureflow.tasks.smoke import ping_task


def test_celery_smoke_task():
    # In eager mode or direct invocation, Celery tasks can be tested synchronously
    result = ping_task.apply(args=["hello-procureflow"]).get()
    assert result["status"] == "success"
    assert result["message"] == "hello-procureflow"
    assert "timestamp" in result
