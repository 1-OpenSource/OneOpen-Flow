from app.executors.auth_verification import AuthVerificationExecutor


def test_extract_otp_from_email_body():
    ex = AuthVerificationExecutor()
    result = ex.execute(
        config={},
        context={
            "node_type": "extract_email_otp",
            "previous_result": {
                "outputs": {"body": "Your verification code is 482913. It expires soon."}
            },
        },
    )
    assert result["status"] == "passed"
    assert result["outputs"]["otp"] == "482913"


def test_extract_verification_link():
    ex = AuthVerificationExecutor()
    result = ex.execute(
        config={"urlContains": "verify"},
        context={
            "node_type": "extract_email_verification_link",
            "previous_result": {
                "outputs": {
                    "html": '<a href="https://app.example.com/verify?token=abc">Confirm email</a>'
                }
            },
        },
    )
    assert result["status"] == "passed"
    assert "verify" in result["outputs"]["verificationUrl"]


def test_generate_totp():
    ex = AuthVerificationExecutor()
    result = ex.execute(
        config={"secret": "JBSWY3DPEHPK3PXP"},
        context={"node_type": "generate_totp", "secrets": {}},
    )
    assert result["status"] == "passed"
    assert len(result["outputs"]["otp"]) == 6


def test_human_otp_pauses_run():
    ex = AuthVerificationExecutor()
    result = ex.execute(
        config={"prompt": "Enter SMS code"},
        context={"node_type": "human_otp_input"},
    )
    assert result["status"] == "approval_required"
    assert result.get("pause") is True
    assert result["outputs"]["inputType"] == "otp"
