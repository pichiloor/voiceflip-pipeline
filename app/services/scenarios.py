import asyncio


async def execute_scenario(scenario: str, attempt: int) -> dict:
    # Simulates handler behavior based on scenario

    if scenario == "ok":
        await asyncio.sleep(0.1)
        return {"message": "success"}

    if scenario == "timeout":
        # Simulate long processing (will trigger timeout)
        await asyncio.sleep(10)
        return {"message": "timeout"}

    if scenario == "transient_fail_then_ok":
        # Fail first 2 attempts, then succeed
        if attempt < 3:
            raise ConnectionError("temporary failure")
        await asyncio.sleep(0.1)
        return {"message": "recovered"}

    if scenario == "hard_fail":
        raise ValueError("permanent failure")

    raise ValueError(f"unknown scenario: {scenario!r}")