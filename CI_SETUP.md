# Travis CI setup and acceptance checks

## Services

1. Sign in to Travis CI with `yuelihe2-svg` and enable `swe1-app` in the
   GitHub integration. Enable both **Build pushed branches** and **Build pushed
   pull requests** in the repository's Travis settings. Keep fork-PR secrets
   disabled. The account needs available build credits.
2. Sign in to Coveralls with the same GitHub account and enable this public
   repository. The Python `coveralls` client recognizes Travis automatically.
   If the repository requires a token, store `COVERALLS_REPO_TOKEN` as a masked
   Travis environment variable, never in Git. Public fork PR builds should use
   Travis job authentication; do not expose AWS secrets to fork builds.
3. Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as masked Travis variables
   restricted to `main`. Use a dedicated IAM deployment identity with access
   to this EB application/environment and its source-bundle S3 prefix. Do not
   use root credentials or short-lived `aws login` credentials for ongoing CI.
4. The existing deployment target is application `swe1-app`, environment
   `swe1-app-287872994760`, region `us-east-1`, source bucket
   `elasticbeanstalk-us-east-1-287872994760`. Verify the bucket and IAM permissions
   against the AWS account before the first CI deployment.

## Pipeline

`.travis.yml` runs Black, flake8 (88 columns), Django system and migration checks,
17 existing tests through coverage.py, and the Coveralls upload. The upload is
in `script`, so a reporting failure is visible as a failed build. Coverage includes
application code and settings; tests, generated migrations and WSGI/ASGI startup
wrappers are excluded. No minimum percentage is required by this assignment.

Only a successful `main` push deploys using Travis's dpl v2 Elastic Beanstalk
provider. PR builds never deploy. The source ZIP uses an explicit application-file
allowlist, excluding credentials, local databases and development environments.
The provider waits for EB to finish, then a live HTTP smoke check runs.

## GitHub

- Invite `slurpysalmon` with **Write** permission. An outstanding invitation needs
  to be accepted by the recipient.
- Protect `main` with required status checks and up-to-date branches. Select the
  actual Travis PR check emitted by a verification PR. The legacy status context
  is `continuous-integration/travis-ci/pr`; a GitHub App integration can emit a
  different check name, which must be matched exactly.

## End-to-end acceptance

1. Open a PR and verify that a Travis PR build starts automatically and is
   attached to the PR in GitHub.
2. Confirm Black, flake8, tests and Coveralls upload pass. Check that the README
   badges resolve and that the coverage report names the tested commit.
3. On a temporary verification branch, introduce a formatting error and confirm
   Black fails. Separately introduce an unused import and confirm flake8 fails.
   Fix the branch and confirm the PR passes again. Never merge failing code.
4. Merge a passing PR. Verify that the `main` build deploys successfully and that
   the EB application version corresponds to that build. Open `/polls/` and
   confirm a 200 response.
5. Submit the three links in `SUBMISSION.md` only after these checks are complete.

## References

- [Travis Python](https://docs.travis-ci.com/user/languages/python/)
- [Travis Elastic Beanstalk deployment v2](https://docs.travis-ci.com/user/deployment-v2/providers/elasticbeanstalk/)
- [Travis Coveralls integration](https://docs.travis-ci.com/user/coveralls/)
- [Black](https://github.com/psf/black)
- [flake8](https://flake8.pycqa.org/en/latest/)
- [coverage.py](https://coverage.readthedocs.io/)
