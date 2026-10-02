.PHONY: test validate audit check package

test:
	python3 -m unittest discover -s tests -p 'test_*.py' -v

validate:
	python3 scripts/validate_skills.py
	python3 shared/scripts/validate_config.py --config shared/templates/config.template.json

audit:
	python3 shared/scripts/release_audit.py --root .

check: test validate audit

package: check
	python3 scripts/package_release.py --root . --dist dist
