def test_required_imports():
    import fastapi
    import numpy
    import pandas
    import scipy
    import sklearn
    from backend.main import app

    assert all((fastapi, numpy, pandas, scipy, sklearn, app))

