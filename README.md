### This is for zipping the project bundle and deploy to a complete new lambda function.
```
cd teamwork-integration-slack-app
poetry install
poetry build
pip install -t dist/lambda . --upgrade
cd dist/lambda; zip -x '*.pyc' -r ../lambda.zip .; cd ../../
aws lambda create-function --function-name tw_slack_app --runtime python3.9 --role arn:aws:iam::700581804758:role/bolt_python_lambda_invocation --handler teamwork_integration_slack_app.app.handler --zip-file fileb://dist/lambda.zip
```
### this is for updating lambda function
```
cd teamwork-integration-slack-app
poetry install
poetry build
pip install -t dist/lambda . --upgrade
cd dist/lambda; zip -x '*.pyc' -r ../lambda.zip .; cd ../../
aws lambda update-function-code --function-name tw_slack_app --zip-file fileb://dist/lambda.zip
```
## I will add a guide for how to host a local app for testing purpose later soon.
```
coming soon
```