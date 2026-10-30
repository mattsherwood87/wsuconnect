#!/opt/conda/envs/aslprep/bin/python3.11
# zmap_cifti_wf.py

# Copywrite: Matthew Sherwood (matt.sherwood@wright.edu, matthew.sherwood.7.ctr@us.af.mil)
# Created on 5 November 2025
#
# This file runs in the python enviroment on pennlinc/aslprep docker image. Must bind mount /resshare/wsuconnect to /resshare/wsuconnect.
#
#versioning

# """
# COMPUTE_SEGSTATS_FSLR WORKFLOW
# ++++++++++++++++++++

# .. autofunction:: init_segstats_wf

# """
import os
import sys

from json import loads
from niworkflows.interfaces.bids import DerivativesDataSink as BaseDerivativesDataSink
from nipype.interfaces.base import (
    CommandLine,
    CommandLineInputSpec,
    File,
    TraitedSpec,
    isdefined,
    traits,
)
from nipype.interfaces.workbench.base import WBCommand



    
class OpenMPTraitedSpec(CommandLineInputSpec):
    num_threads = traits.Int(desc='allows for specifying more threads')

class OpenMPCommandMixin(CommandLine):
    input_spec = OpenMPTraitedSpec

    _num_threads = None

    def __init__(self, **inputs):
        super().__init__(**inputs)
        self.inputs.on_trait_change(self._num_threads_update, 'num_threads')
        if not self._num_threads:
            self._num_threads = os.environ.get('OMP_NUM_THREADS', None)
        if not isdefined(self.inputs.num_threads) and self._num_threads:
            self.inputs.num_threads = int(self._num_threads)
        self._num_threads_update()

    def _num_threads_update(self):
        if self.inputs.num_threads:
            self.inputs.environ.update({'OMP_NUM_THREADS': str(self.inputs.num_threads)})

    def run(self, **inputs):
        if 'num_threads' in inputs:
            self.inputs.num_threads = inputs['num_threads']
        self._num_threads_update()
        return super().run(**inputs)

class CiftiMathInputSpec(OpenMPTraitedSpec):
    
    expression = traits.String(
        mandatory=True,
        desc="the expression to evaluate, e.g. '(A + B) / 2'",
        argstr='"%s"',
        position=0
    )
    cifti_out = File(
        "cifti_math.dscalar.nii",
        usedefault=True,
        exists=False,
        argstr="%s",
        position=1,
        desc="Name of output CIFTI file"
    )
    fixnan = traits.Int(
        default_value=3,
        argstr='-fixnan %d',
        desc='replace NaN results with value'
    )
    # var_names = traits.List(traits.Str, mandatory=True)
    A_file= File(
        exists=True,
        mandatory=False,
        argstr="-var A %s"
    )
    B_file = File(
        exists=True,
        mandatory=False,
        argstr="-var B %s"
    )
    # variables = traits.Dict(
    #     key_trait=traits.Str(),
    #     value_trait=File(exists=True),
    #     mandatory=True,
    #     desc="Mapping of variable name → CIFTI input file",
    #     argstr=None,
    #     position=2
    # )
    # _varstr = traits.Str(argstr="%s")  # dummy trait for CLI


class CiftiMathOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Output CIFTI file")


class CiftiMath(WBCommand, OpenMPCommandMixin):
    """EVALUATE EXPRESSION ON CIFTI FILES.

      This command evaluates <expression> at each matrix element independently.
      There must be at least one -var option (to get the output layout from),
      even if the <name> specified in it isn't used in <expression>.

      To select a single column from a 2D file (most cifti files are 2D), use
      -select 1 <index>, where <index> is 1-based.  To select a single row from
      a 2D file, use -select 2 <index>.  Where -select is not used, the cifti
      files must have compatible mappings (e.g., brain models and parcels
      mappings must match exactly except for parcel names).  Use
      -override-mapping-check to skip this checking.

      Filenames are not valid in <expression>, use a variable name and a -var
      option with matching <name> to specify an input file.  The format of
      <expression> is as follows:

      Expressions consist of constants, variables, operators, parentheses, and
      functions, in infix notation, such as 'exp(-x + 3) * scale'.  Variables
      are strings of any length, using the characters a-z, A-Z, 0-9, and _, but
      may not take the name of a named constant.  Currently, there is only one
      named constant, PI.  The operators are +, -, *, /, ^, >, <, >=, <=, ==,
      !=, !, &&, ||.  These behave as in C, except that ^ is exponentiation,
      i.e. pow(x, y), and takes higher precedence than other binary operators
      (also, '-3^-4^-5' means '-(3^(-(4^-5)))').  The <=, >=, ==, and !=
      operators are given a small amount of wiggle room, equal to one millionth
      of the smaller of the absolute values of the values being compared.

      Comparison and logical operators return 0 or 1, you can do masking with
      expressions like 'x * (mask > 0)'.  For all logical operators, an input
      is considered true iff it is greater than 0.  The expression '0 < x < 5'
      is not syntactically wrong, but it will NOT do what is desired, because
      it is evaluated left to right, i.e. '((0 < x) < 5)', which will always
      return 1, as both possible results of a comparison are less than 5.  A
      warning is generated if an expression of this type is detected.  Use
      something like 'x > 0 && x < 5' to get the desired behavior.

      Whitespace between elements is ignored, ' sin ( 2 * x ) ' is equivalent
      to 'sin(2*x)', but 's in(2*x)' is an error.  Implied multiplication is
      not allowed, the expression '2x' will be parsed as a variable.
      Parentheses are (), do not use [] or {}.  Functions require parentheses,
      the expression 'sin x' is an error.

      The following functions are supported:

         sin: 1 argument, the sine of the argument (units are radians)
         cos: 1 argument, the cosine of the argument (units are radians)
         tan: 1 argument, the tangent of the argument (units are radians)
         asin: 1 argument, the inverse of sine of the argument, in radians
         acos: 1 argument, the inverse of cosine of the argument, in radians
         atan: 1 argument, the inverse of tangent of the argument, in radians
         atan2: 2 arguments, atan2(y, x) returns the inverse of tangent of
      (y/x), in radians, determining quadrant by the sign of both arguments
         sinh: 1 argument, the hyperbolic sine of the argument
         cosh: 1 argument, the hyperbolic cosine of the argument
         tanh: 1 argument, the hyperbolic tangent of the argument
         asinh: 1 argument, the inverse hyperbolic sine of the argument
         acosh: 1 argument, the inverse hyperbolic cosine of the argument
         atanh: 1 argument, the inverse hyperbolic tangent of the argument
         sinc: 1 argument, sinc(0) = 1, sin(x) / x otherwise
         ln: 1 argument, the natural logarithm of the argument
         exp: 1 argument, the constant e raised to the power of the argument
         log: 1 argument, the base 10 logarithm of the argument
         log2: 1 argument, the base 2 logarithm of the argument
         sqrt: 1 argument, the square root of the argument
         abs: 1 argument, the absolute value of the argument
         floor: 1 argument, the largest integer not greater than the argument
         round: 1 argument, the nearest integer, with ties rounded away from
      zero
         ceil: 1 argument, the smallest integer not less than the argument
         min: 2 arguments, min(x, y) returns y if (x > y), x otherwise
         max: 2 arguments, max(x, y) returns y if (x < y), x otherwise
         mod: 2 arguments, mod(x, y) = x - y * floor(x / y), or 0 if y == 0
         clamp: 3 arguments, clamp(x, low, high) = min(max(x, low), high)
    """

    _cmd = "wb_command -cifti-math "
    input_spec = CiftiMathInputSpec
    output_spec = CiftiMathOutputSpec

    # def _format_arg(self, name, spec, value):
    #     """Formats the variable dictionary into CLI args."""
        
    #     # if name == "expression" and value:
    #     #     # wrap the expression in double quotes
    #     #     return f'"{value}"'
    #     # if name == "variables":
    #     #     args = []
    #     #     for k, v in value.items():
    #     #         args += ['-var', k, v]
    #     #     return " ".join(args)
    #     # if name == "_varstr":
    #     #     # generate string from variables dict
    #     #     var_dict = getattr(self.inputs, "variables", {})
    #     #     return " ".join([f"-var {k} {v}" for k, v in var_dict.items()])
    #     if name == "var_names":
    #         # generate -var tokens from var_names + var_files
    #         var_files = getattr(self.inputs, "var_files")
    #         if len(var_files) != len(value):
    #             raise ValueError("var_names and var_files must be same length")
    #         parts = []
    #         for n, f in zip(value, var_files):
    #             parts += ["-var", n, f]
    #         return " ".join(parts)
    #     return super()._format_arg(name, spec, value)

    def _list_outputs(self):
        outputs = self.output_spec().get()
        outputs["out_file"] = os.path.abspath(self.inputs.cifti_out)
        return outputs


class CiftiParcellateInputSpec(OpenMPTraitedSpec):
    cifti_in = File(
        exists=True,
        mandatory=True,
        position=0,
        desc="Input CIFTI file (dtseries / dscalar / pscalar)",
        argstr="%s"
    )
    cifti_label = File(
        exists=True,
        mandatory=True,
        position=1,
        desc="CIFTI dlabel file defining parcel boundaries",
        argstr="%s"
    )
    direction = traits.Enum(
        "COLUMN", "ROW",
        usedefault=True,
        position=2,
        desc="Apply parcellation across rows or columns",
        argstr="%s"
    )
    cifti_out = File(
        "parcellated.ptseries.nii",
        usedefault=True,
        position=3,
        desc="Output CIFTI parcel file",
        argstr="%s"
    )
    method = traits.Enum(
        "MEAN",
        "MEDIAN",
        "MAX",
        "MIN",
        "INDEXMAX",
        "INDEXMIN",
        "SUM",
        "PRODUCT",
        "MODE",
        "STDEV",
        "SAMPSTDEV",
        "TSNR",
        "VARIANCE",
        "COV",
        "L2NORM",
        "COUNT_NONZERO",
        desc="Optional aggregation method (used with -method flag)",
        argstr="-method %s",
        usedefault=False
    )
    cifti_weights = File(
        exists=True,
        desc="Optional area/volume metric CIFTI file for weighted parcellation",
        argstr="-cifti-weights %s"
    )
    exclude_outliers = traits.Either(
        None,
        traits.Tuple(traits.String(), traits.String()),
        argstr="-exclude-outliers %s %s",
        desc="Exclude outliers: MIN MAX"
    )
    only_numeric = traits.Bool(False, desc="Exclude non-numeric values",argstr="-only-numeric")

    non_empty_mask_out = File(
        "mask_out.pscalar.nii",
        desc="output_mask_file",
        argstr="-nonempty-mask-out %s")
    # spatial_weights = traits.Bool(False, desc="Apply spatial smoothing weights")


class CiftiParcellateOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Output CIFTI file")


class CiftiParcellate(WBCommand, OpenMPCommandMixin):
    """PARCELLATE A CIFTI FILE

      Each label (other than the unlabeled key) in the cifti label file will be
      treated as a parcel, and all rows or columns of data within the parcel
      are averaged together to form the parcel's output row or column.  If
      -legacy-mode is specified, parcels will be defined as the overlap between
      a label and the data, with no errors for missing data vertices or voxels,
      and empty parcels discarded.  The direction can be either an integer
      starting from 1, or the strings 'ROW' or 'COLUMN'.  For dtseries or
      dscalar, use COLUMN.  If you are parcellating a dconn in both directions,
      parcellating by ROW first will use much less memory.

      NOTE: the parcels in the output file are sorted by the numeric label
      keys, in ascending order.

      The parameter to the -method option must be one of the following:

      MAX: the maximum value
      MIN: the minimum value
      INDEXMAX: the 1-based index of the maximum value
      INDEXMIN: the 1-based index of the minimum value
      SUM: add all values
      PRODUCT: multiply all values
      MEAN: the mean of the data
      STDEV: the standard deviation (N denominator)
      SAMPSTDEV: the sample standard deviation (N-1 denominator)
      VARIANCE: the variance of the data
      TSNR: mean divided by sample standard deviation (N-1 denominator)
      COV: sample standard deviation (N-1 denominator) divided by mean
      L2NORM: square root of sum of squares
      MEDIAN: the median of the data
      MODE: the mode of the data
      COUNT_NONZERO: the number of nonzero elements in the data

      The -*-weights options are mutually exclusive and may only be used with
      MEAN (default), SUM, STDEV, SAMPSTDEV, VARIANCE, MEDIAN, or MODE (default
      for label data).
    """
    _cmd = "wb_command -cifti-parcellate"
    input_spec = CiftiParcellateInputSpec
    output_spec = CiftiParcellateOutputSpec

    def _format_arg(self, name, spec, value):
        return super()._format_arg(name, spec, value)

    def _list_outputs(self):
        out = self.output_spec().get()
        out["out_file"] = os.path.abspath(self.inputs.cifti_out)
        return out


class CiftiConvertToTextInputSpec(OpenMPTraitedSpec):
    cifti_in = File(
        exists=True,
        mandatory=True,
        position=0,
        desc="Input CIFTI file (dtseries / dscalar / pscalar)",
        argstr="%s"
    )
    text_out = File(
        "parcellated.dscalar.txt",
        usedefault=True,
        position=1,
        desc="Output CIFTI parcel file",
        argstr="%s"
    )
    col_delim = traits.String(
        mandatory=False,
        desc="choose string to put between elements in a row, default is tab",
        argstr="-col-delim %s"
    )


class CiftiConvertToTextOutputSpec(TraitedSpec):
    out_file = File(exists=True, desc="Output TEXT file")


class CiftiConvertToText(WBCommand, OpenMPCommandMixin):
    """DUMP CIFTI MATRIX INTO TEXT FORMAT

      This command is used to convert a full CIFTI matrix to text format that
      can be used by programs that don't understand CIFTI. 

      This command cannot map surface-based parts of the cifti file to a
      spatially-correct volume file, or map volume-based data to the surface,
      see -volume-to-surface-mapping and -metric-to-volume-mapping instead
      (other commands such as -cifti-separate are also required).

      If you want to write an existing CIFTI file with a different CIFTI
      version, see -file-convert, and its -cifti-version-convert option.

      If you want part of the CIFTI file as a metric, label, or volume file,
      see -cifti-separate.  If you want to create a CIFTI file from metric
      and/or volume files, see the -cifti-create-* commands.

      If you want to import a matrix in non-CIFTI format that is restricted to
      an ROI, first obtain a template CIFTI file matching that ROI (you can use
      -cifti-create-dense-scalar if you don't have such a file).  Use
      -cifti-convert to import it to CIFTI format, and you can then expand the
      file into a standard brainordinates space with
      -cifti-create-dense-from-template.  If you want to export only part of a
      CIFTI file, first create an roi-restricted CIFTI file with
      -cifti-restrict-dense-mapping.
    """
    _cmd = "wb_command -cifti-convert -to-text"
    input_spec = CiftiConvertToTextInputSpec
    output_spec = CiftiConvertToTextOutputSpec

    def _format_arg(self, name, spec, value):
        return super()._format_arg(name, spec, value)

    def _list_outputs(self):
        out = self.output_spec().get()
        out["out_file"] = os.path.abspath(self.inputs.text_out)
        return out