from run import create_app


def test_file_types_api_html_grouping():
    app = create_app()
    client = app.test_client()
    resp = client.get('/api/config/file-types')
    data = resp.get_json()
    assert data['status'] == 'success'
    groups = data['data']
    html_group = groups.get('html_to_markdown_types')
    assert html_group is not None and any(t['ext'] == 'html' for t in html_group)
    structured_group = groups.get('structured_to_markdown_types')
    assert structured_group is not None
    # Ensure html/htm are not in structured group
    assert all(t['ext'] not in ('html','htm') for t in structured_group)