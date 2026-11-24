"""Make a copy of the Kokoro ONNX model that also outputs per-phoneme durations.

kokoro-onnx returns phoneme timings (used for lip sync) only when the model has an
output named "duration". The stock v1.0 model computes the durations internally
(`/encoder/Gather_output_0`, the tensor fed into CumSum) but doesn't expose them,
so we add it as a graph output. Audio output is unchanged.

Usage: python3 make_timed_model.py /path/kokoro.onnx /path/kokoro-timed.onnx
"""
import sys
import onnx
from onnx import helper, TensorProto

src, dst = sys.argv[1], sys.argv[2]
m = onnx.load(src)
g = m.graph
if "duration" not in [o.name for o in g.output]:
    g.node.append(helper.make_node("Identity", ["/encoder/Gather_output_0"], ["duration"], name="expose_duration"))
    g.output.append(helper.make_tensor_value_info("duration", TensorProto.INT64, ["num_tokens"]))
onnx.save(m, dst)
print("timed model saved:", dst)
