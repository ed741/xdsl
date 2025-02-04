import re
from io import StringIO
from typing import Annotated
from xdsl.ir import (Attribute, Data, MLContext, TypeAttribute, Operation,
                     ParametrizedAttribute, Region)
from xdsl.irdl import (AnyAttr, ParameterDef, VarOpResult, VarOperand,
                       irdl_attr_definition, irdl_op_definition)
from xdsl.parser import BaseParser, XDSLParser
from xdsl.printer import Printer


@irdl_op_definition
class ModuleOp(Operation):
    """Module operation. Redefined to not depend on the builtin dialect."""
    name = "module"
    region: Region


@irdl_op_definition
class AnyOp(Operation):
    """Operation only used for testing."""
    name = "any"
    op: Annotated[VarOperand, AnyAttr()]
    res: Annotated[VarOpResult, AnyAttr()]


@irdl_attr_definition
class DataAttr(Data[int]):
    """Attribute only used for testing."""
    name = "data_attr"

    @staticmethod
    def parse_parameter(parser: BaseParser) -> int:
        return parser.parse_int_literal()

    def print_parameter(self, printer: Printer) -> None:
        printer.print(self.data)


@irdl_attr_definition
class DataType(Data[int], TypeAttribute):
    """Attribute only used for testing."""
    name = "data_type"

    @staticmethod
    def parse_parameter(parser: BaseParser) -> int:
        return parser.parse_int_literal()

    def print_parameter(self, printer: Printer) -> None:
        printer.print(self.data)


@irdl_attr_definition
class ParamAttr(ParametrizedAttribute):
    name = "param_attr"


@irdl_attr_definition
class ParamAttrWithParam(ParametrizedAttribute):
    name = "param_attr_with_param"
    data: ParameterDef[Attribute]


@irdl_attr_definition
class ParamType(ParametrizedAttribute, TypeAttribute):
    name = "param_type"


@irdl_attr_definition
class ParamAttrWithCustomFormat(ParametrizedAttribute):
    name = "param_custom_format"
    param1: ParameterDef[ParamAttr]

    def print_parameters(self, printer: Printer) -> None:
        printer.print("~~")


def print_as_mlir_and_compare(test_prog: str, expected: str):
    ctx = MLContext()

    ctx.register_op(ModuleOp)
    ctx.register_op(AnyOp)
    ctx.register_attr(DataAttr)
    ctx.register_attr(DataType)
    ctx.register_attr(ParamAttr)
    ctx.register_attr(ParamType)
    ctx.register_attr(ParamAttrWithParam)
    ctx.register_attr(ParamAttrWithCustomFormat)

    parser = XDSLParser(ctx, test_prog)
    module = parser.parse_operation()

    res = StringIO()
    printer = Printer(target=Printer.Target.MLIR, stream=res)
    printer.print_op(module)

    # Remove all whitespace from the expected string.
    regex = re.compile(r'[^\S]+')
    assert (regex.sub("", res.getvalue()).strip() == \
            regex.sub("", expected).strip())


def test_empty_op():
    """Test printing an empty operation."""
    print_as_mlir_and_compare(
        """any()""",
        """"any"() : () -> ()""",
    )


def test_data_attr():
    """Test printing an operation with a data attribute."""
    print_as_mlir_and_compare(
        """any() [ "attr" = !data_attr<42> ]""",
        """"any"() {"attr" = #data_attr<42>} : () -> ()""",
    )


def test_data_type():
    """Test printing an operation with a data type."""
    print_as_mlir_and_compare(
        """%0 : !data_type<42> = any()""",
        """%0 = "any"() : () -> !data_type<42>""",
    )


def test_param_attr():
    """Test printing an operation with a parametrized attribute."""
    print_as_mlir_and_compare(
        """any() [ "attr" = !param_attr ]""",
        """"any"() {"attr" = #param_attr } : () -> ()""",
    )


def test_param_type():
    """Test printing an operation with a parametrized type."""
    print_as_mlir_and_compare(
        """%0 : !param_type = any()""",
        """%0 = "any"() : () -> !param_type""",
    )


def test_param_attr_with_param():
    """
    Test printing an operation with a parametrized attribute with parameters.
    """
    print_as_mlir_and_compare(
        """any() [ "attr" = !param_attr_with_param<!param_attr> ]""",
        """"any"() {"attr" = #param_attr_with_param<#param_attr> }
          : () -> ()""",
    )

    print_as_mlir_and_compare(
        """any() [ "attr" = !param_attr_with_param<!param_type> ]""",
        """"any"() {"attr" = #param_attr_with_param<!param_type> }
          : () -> ()""",
    )


def test_op_with_region():
    """Test printing an operation with a region."""

    print_as_mlir_and_compare(
        """module() {}""",
        """"module"() ({}) : () -> ()""",
    )


def test_op_with_results():
    """Test printing an operation with results."""

    print_as_mlir_and_compare(
        """%0 : !param_attr = any()""",
        """%0 = "any"() : () -> #param_attr""",
    )

    print_as_mlir_and_compare(
        """%0 : !param_attr, %1 : !param_type = any()""",
        """%0, %1 = "any"() : () -> (#param_attr, !param_type)""",
    )


def test_op_with_operands():
    """Test printing an operation with operands."""
    print_as_mlir_and_compare(
        """module() {
           %0 : !param_attr = any()
           any(%0 : !param_attr)
        }""",
        """"module"() ({
              %0 = "any"() : () -> #param_attr
              "any"(%0) : (#param_attr) -> ()
            }) : () -> ()
        """,
    )

    print_as_mlir_and_compare(
        """module() {
           %0 : !param_attr = any()
           any(%0 : !param_attr, %0 : !param_attr)
        }""",
        """"module"() ({
              %0 = "any"() : () -> #param_attr
              "any"(%0, %0) : (#param_attr, #param_attr) -> ()
            }) : () -> ()
        """,
    )


def test_op_with_attributes():
    """Test printing an operation with attributes."""
    print_as_mlir_and_compare(
        """any() [ "attr" = !data_attr<42> ]""",
        """"any"() {"attr" = #data_attr<42>} : () -> ()""",
    )


def test_param_custom_format():
    """Test printing an operation with a param attribute with custom format."""
    print_as_mlir_and_compare(
        """any() [ "attr" = !param_custom_format<!param_attr> ]""",
        """"any"() {"attr" = #param_custom_format~~} : () -> ()""",
    )
