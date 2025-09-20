import pytest
from run import create_app


@pytest.fixture(scope='session')
def app_instance():
	app = create_app()
	return app


@pytest.fixture()
def app_context(app_instance):
	with app_instance.app_context():
		yield

