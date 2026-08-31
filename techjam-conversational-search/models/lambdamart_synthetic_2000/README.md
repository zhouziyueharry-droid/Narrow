# Trained LambdaMART model

This opt-in bundle contains model.txt, metadata.json, and idf.json. Keep all three together.
`same_data_linear_weights.json` contains the frozen linear control used by online audit logging; keep it with the bundle when running traced evaluations. These are model weights, not an old evaluation result.
It is the 167-tree model evaluated on all 200 official samples, with 1291 synthetic training and 291 validation sessions.
The default application ranker remains PreciseReranker. Install the ltr extra before loading this bundle.

The model and IDF bytes are unchanged from the local evaluation bundle. The metadata source path is made relative; all training hashes and settings are retained.
The original source JSONL has the same parsed records as data/synthetic_scenarios_2000.jsonl; its byte hash differs due to file formatting.

SHA256 model.txt: d4243775f26f8fc5b651becd0100d6a69d232401b73b7371f1c9e0bc4f72b79a

SHA256 idf.json: 0dc41598feb7af5f6021ccda450ced0aa059a6c75f60daae6de8939f54830935

See the [latest evaluation report](../../docs/lambdamart_online_pro_report.md), [training details](../../docs/lambdamart_training.md), and [project README](../../../README.md) for evaluation and usage.
