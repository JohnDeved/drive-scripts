"""Type stubs for ipywidgets."""

from typing import Any, Callable, Dict, List, Optional, Tuple, Union

class Layout:
    def __init__(
        self,
        width: Optional[str] = None,
        height: Optional[str] = None,
        margin: Optional[str] = None,
        padding: Optional[str] = None,
        display: Optional[str] = None,
        gap: Optional[str] = None,
        max_height: Optional[str] = None,
        overflow: Optional[str] = None,
        border: Optional[str] = None,
        **kwargs: Any,
    ) -> None: ...

class Widget:
    layout: Layout
    def observe(
        self, handler: Callable[..., None], names: Union[str, List[str]] = ...
    ) -> None: ...
    def unobserve(
        self, handler: Callable[..., None], names: Union[str, List[str]] = ...
    ) -> None: ...

class HTML(Widget):
    value: str
    def __init__(self, value: str = "", **kwargs: Any) -> None: ...

class Button(Widget):
    description: str
    button_style: str
    icon: str
    disabled: bool
    def __init__(
        self,
        description: str = "",
        button_style: str = "",
        icon: str = "",
        layout: Optional[Layout] = None,
        **kwargs: Any,
    ) -> None: ...
    def on_click(self, callback: Callable[[Any], None]) -> None: ...

class Dropdown(Widget):
    options: Union[Dict[str, Any], List[Tuple[str, Any]]]
    value: Any
    description: str
    disabled: bool
    def __init__(
        self,
        options: Union[Dict[str, Any], List[Tuple[str, Any]]] = ...,
        description: str = "",
        layout: Optional[Layout] = None,
        **kwargs: Any,
    ) -> None: ...

class Checkbox(Widget):
    value: bool
    description: str
    disabled: bool
    indent: bool
    def __init__(
        self,
        value: bool = False,
        description: str = "",
        indent: bool = True,
        **kwargs: Any,
    ) -> None: ...

class Text(Widget):
    value: str
    placeholder: str
    continuous_update: bool
    description: str
    def __init__(
        self,
        value: str = "",
        placeholder: str = "",
        continuous_update: bool = False,
        description: str = "",
        layout: Optional[Layout] = None,
        **kwargs: Any,
    ) -> None: ...

class FloatProgress(Widget):
    value: float
    min: float
    max: float
    bar_style: str
    def __init__(
        self,
        value: float = 0,
        min: float = 0,
        max: float = 100,
        bar_style: str = "",
        layout: Optional[Layout] = None,
        **kwargs: Any,
    ) -> None: ...

class Output(Widget):
    def __init__(self, layout: Optional[Layout] = None, **kwargs: Any) -> None: ...
    def clear_output(self, wait: bool = False) -> None: ...
    def __enter__(self) -> "Output": ...
    def __exit__(self, *args: Any) -> None: ...

class Box(Widget):
    children: Tuple[Widget, ...]
    def __init__(
        self,
        children: List[Widget] = ...,
        layout: Optional[Layout] = None,
        **kwargs: Any,
    ) -> None: ...

class HBox(Box): ...
class VBox(Box): ...
