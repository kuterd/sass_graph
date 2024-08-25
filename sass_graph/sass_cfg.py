"""
Generate Control Flow Graph from SASS dump of a program.
"""

import subprocess
from .parser import InstructionParser, LabelOperand
from . import parser
import html

import json
import jinja2


class Node:
    def __init__(self, name, lines):
        self.name = name
        self.lines = lines
        self._vertex = None
        self.target_names = []

    def encode(self):
        return {
            "name": self.name,
            "lines": self.lines,
            "edges": self.target_names,
        }


class CFGGraph:
    def __init__(self):
        self.nodes = {}
        self._edges = []
        self.entry = None

    def add_node(self, node):
        if len(self.nodes) == 0:
            self.entry = node

        self.nodes[node.name] = node

    def generate(self):
        encoded_graph = {"nodes": {}}
        for node in self.nodes.values():
            encoded_graph["nodes"][node.name] = node.encode()

        file_loader = jinja2.FileSystemLoader("templates")
        env = jinja2.Environment(loader=file_loader)

        template = env.get_template("template.html")
        result = template.render({"json_data": json.dumps(encoded_graph)})
        return result

    def dump(self, filename):
        result_file = open(filename, "w")
        result_file.write(self.generate())
        result_file.close()


seperator = "//---------------------"


def _process_dump(dump):
    lines = dump.split("\n")

    sections = {}

    current_section = []
    for line in lines:
        if line.startswith(seperator):
            current_section = []

            name = line[len(seperator) :]
            name = name[: name.find("-")].strip()
            sections[name] = current_section
            continue

        current_section.append(line)

    return sections


def disassemble(file_name, nvdisasm="nvdisasm"):
    result = subprocess.run([nvdisasm, file_name], capture_output=True)
    return _process_dump(result.stdout.decode("ascii"))


TEXT_PREFIX = ".text."


def colored_section(color, text):
    return f'<span style="color: {color}">{html.escape(text)}</span>'


OPERAND_CORE_COLOR = "green"
SPECIAL_REG_COLOR = "darkorange"
PREDICATE_COLOR = "red"
UNIFORM_COLOR = "blue"

INSTRUCTION_COLOR = "black"
CONSTANT_COLOR = "black"


class SyntaxtHighlighter:
    def visit_operand(self, operand):
        if isinstance(operand, parser.RegOperand):
            color = OPERAND_CORE_COLOR
            if operand.reg_type == "SR":
                color = SPECIAL_REG_COLOR
            elif operand.reg_type == "UR":
                color = UNIFORM_COLOR
            elif operand.reg_type == "P" or operand.reg_type == "UP":
                color = PREDICATE_COLOR

            return colored_section(
                color,
                repr(operand),
            )
        elif isinstance(operand, parser.LabelOperand):
            return colored_section(CONSTANT_COLOR, repr(operand))
        elif isinstance(operand, parser.AddressOperand):
            result = "+".join([self.visit_operand(a) for a in operand.sub_operands])
            return f"[{result}]"
        elif isinstance(operand, parser.IntIMMOperand) or isinstance(
            operand, parser.FloatIMMOperand
        ):
            return colored_section(CONSTANT_COLOR, repr(operand))
        elif isinstance(operand, parser.DescOperand):
            prefix = "g" if self.g else ""
            return (
                prefix
                + f"desc[{self.visit_operand(operand.sub_operands[0])}]{self.visit_operand(operand.sub_operands[1])}"
            )
        elif isinstance(operand, parser.AttributeOperand):
            return "a" + self.visit_operand(operand.sub_operands[0])
        elif isinstance(operand, parser.ConstantMemOperand):
            prefix = "cx" if operand.cx else "c"
            return f"{prefix}[{self.visit_operand(operand.sub_operands[0])}]{self.visit_operand(operand.sub_operands[1])}"

        else:
            print("Unsupported", type(operand).__name__)

        return ""

    def highlight(self, instruction):
        result = ""

        if instruction.predicate:
            result += colored_section(PREDICATE_COLOR, instruction.predicate) + " "

        inst_name = instruction.base_name
        if len(instruction.modifiers) > 0:
            inst_name += "." + (".".join(instruction.modifiers))

        result += colored_section(INSTRUCTION_COLOR, inst_name)

        for i, operand in enumerate(instruction.operands):
            if i != 0:
                result += ","
            result += " " + self.visit_operand(operand)

        return result


def generate_cfgs(sections):
    highligher = SyntaxtHighlighter()
    functions = {}
    for name, section in sections.items():
        if not name.startswith(TEXT_PREFIX):
            continue

        graph = CFGGraph()
        function_name = name[len(TEXT_PREFIX) :]
        current_block = Node("entry", [])
        graph.add_node(current_block)
        last_node = current_block
        for line in section[section.index(function_name + ":") + 2 :]:
            if "/*" in line:
                inst = line[line.index("*/") + 2 :].strip()

                parsed = None
                try:
                    parsed = InstructionParser.parseInstruction(inst)
                    current_block.lines.append(highligher.highlight(parsed))
                except Exception:
                    pass
                if not parsed:
                    current_block.lines.append(inst)

                if (
                    parsed
                    and parsed.base_name == "BRA"
                    and isinstance(parsed.operands[0], LabelOperand)
                ):
                    target_name = parsed.operands[0].label_name
                    current_block.target_names.append(target_name)

            elif line.endswith(":"):
                label = line[:-1]
                current_block = Node(label, [colored_section(CONSTANT_COLOR, line)])
                graph.add_node(current_block)
                last_node.target_names.append(label)
                last_node = current_block
        functions[function_name] = graph
    return functions
