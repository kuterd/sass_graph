import html


def display_cfg(func, width="600px", height="600px"):
    from IPython.display import HTML

    # Define HTML content to be embedded directly within the iframe
    html_content = f"""
    <iframe
        width='{html.escape(width)}' height='{html.escape(height)}'
        srcdoc='{html.escape(func.generate())}'>
    </iframe>
    """
    # Display the HTML content with the iframe
    return HTML(html_content)
