"""Office and PDF documents as Markdown (TOOL-14).

The dispatcher :func:`convert` arrives in a later task. This module exists first so the
package imports without any of the optional parser libraries: every converter imports its
library inside the function, and a missing library becomes one refusal that names the extra.
"""
