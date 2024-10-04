from log10._httpx_utils import _try_post_graphql_request
from log10.llm import Log10Config


log10_config = Log10Config()


def create_log10_test_run(eval_name: str):
    query = """
    mutation CreateTestRun($input: CreateTestRunInput!) {
      createTestRun(input: $input) {
        id
        name
        reportUploadUrl
        createdAt
      }
    }
    """

    variables = {"input": {"name": eval_name, "organizationId": log10_config.org_id}}

    response = _try_post_graphql_request(query, variables)

    if response and response.status_code == 200:
        data = response.json()
        return data.get("data", {}).get("createTestRun", {})
    else:
        return {}
