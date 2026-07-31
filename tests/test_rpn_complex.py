import pytest

from mcp_calculator.errors import CalcError
from mcp_calculator.rpn import evaluate


def test_cmplx_abs():
    r = evaluate("3 4 cmplx abs")
    assert r["result"] == pytest.approx(5)


def test_complex_literal():
    r = evaluate("3+4j abs")
    assert r["result"] == pytest.approx(5)


def test_re_im_conj():
    r = evaluate("3 4 cmplx conj")
    assert r["result"]["re"] == pytest.approx(3)
    assert r["result"]["im"] == pytest.approx(-4)


def test_fact_on_complex_domain_error():
    with pytest.raises(CalcError) as ei:
        evaluate("3 4 cmplx fact")
    assert ei.value.code == "domain_error"
