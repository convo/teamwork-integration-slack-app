cd teamwork-integration-slack-app
poetry install
poetry build
pip install -t dist/lambda . --upgrade
cd dist/lambda; zip -x '*.pyc' -r ../lambda.zip .; cd ../../
# this is for updating lambda function
aws lambda update-function-code --function-name tw_slack_app --zip-file fileb://dist/lambda.zip
# uncomment and run this to create lambda function only if you don't have an existing one.
# aws lambda create-function --function-name tw_slack_app --runtime python3.9 --role arn:aws:iam::700581804758:role/bolt_python_lambda_invocation --handler teamwork_integration_slack_app.app.handler --zip-file fileb://dist/lambda.zip