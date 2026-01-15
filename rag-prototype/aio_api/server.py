"""
ECR API Server - REST API for the AIO/ECR pipeline.

Designed for integration with:
- n8n workflows (HTTP Request node)
- LangChain (custom retriever)
- Any RAG system that can make HTTP calls

Endpoints:
- POST /api/v1/process - Process raw content into clean envelope
- GET  /api/v1/envelope/{id} - Get stored envelope
- GET  /api/v1/anchor/{envelope_id}/{anchor_id} - Get anchor content
- GET  /api/v1/entities - Query entities
- GET  /api/v1/stats - Storage statistics
- GET  /health - Health check
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, request, jsonify
from aio_core.pipeline import AIOPipeline
from aio_api.storage import EnvelopeStorage

app = Flask(__name__)

# Initialize components
pipeline = AIOPipeline()
storage = EnvelopeStorage(os.environ.get('ECR_DB_PATH', 'envelopes.db'))


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "version": "0.1.0",
        "storage": storage.get_stats()
    })


@app.route('/api/v1/process', methods=['POST'])
def process_content():
    """
    Process raw content into a clean AIO envelope.
    
    Request body:
    {
        "content": "raw HTML or markdown content",
        "source": "document.pdf or https://example.com",
        "content_type": "html" | "markdown" (default: "html"),
        "store": true | false (default: true)
    }
    
    Response:
    {
        "envelope_id": "doc-a7f3b2c1",
        "clean_content": "## Clean markdown...",
        "token_count": 856,
        "noise_score": 0.47,
        "noise_removed": "47%",
        "anchors": {...},
        "entities": [...],
        "integrity": {...}
    }
    """
    data = request.get_json()
    
    if not data or 'content' not in data:
        return jsonify({"error": "Missing 'content' field"}), 400
    
    content = data['content']
    source = data.get('source', 'unknown')
    content_type = data.get('content_type', 'html')
    should_store = data.get('store', True)
    
    try:
        # Process through pipeline
        if content_type == 'html':
            result = pipeline.process_with_report(content, source, 'web')
        else:
            envelope = pipeline.process_markdown(content, source, 'markdown')
            result = {"envelope": envelope, "report": {
                "noise_stripping": {
                    "noise_score": envelope.narrative.noise_score,
                    "final_tokens": envelope.narrative.token_count
                }
            }}
        
        envelope = result['envelope']
        report = result.get('report', {})
        
        # Store if requested
        if should_store:
            storage.store_envelope(envelope)
        
        # Build response
        noise_score = envelope.narrative.noise_score
        
        return jsonify({
            "envelope_id": envelope.id,
            "clean_content": envelope.narrative.content,
            "token_count": envelope.narrative.token_count,
            "noise_score": noise_score,
            "noise_removed": f"{noise_score:.0%}",
            "anchors": {
                aid: {
                    "type": a.type,
                    "title": a.title,
                    "lines": f"{a.line_start}-{a.line_end}"
                }
                for aid, a in envelope.anchors.items()
            },
            "entities": [
                {
                    "type": e.type,
                    "properties": e.properties,
                    "anchor_ref": e.anchor_ref
                }
                for e in envelope.entities
            ],
            "integrity": {
                "narrative_hash": envelope.integrity.narrative_hash,
                "generated_at": envelope.integrity.generated_at
            },
            "stored": should_store
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/v1/envelope/<envelope_id>', methods=['GET'])
def get_envelope(envelope_id: str):
    """
    Get a stored envelope by ID.
    
    Response: Full envelope JSON
    """
    envelope = storage.get_envelope(envelope_id)
    
    if not envelope:
        return jsonify({"error": f"Envelope '{envelope_id}' not found"}), 404
    
    return jsonify(envelope)


@app.route('/api/v1/anchor/<envelope_id>/<anchor_id>', methods=['GET'])
def get_anchor(envelope_id: str, anchor_id: str):
    """
    Get content for a specific anchor.
    
    This is the key endpoint for citation lookup:
    - Vector DB returns chunk with anchor_id in metadata
    - Call this endpoint to get the exact source text
    
    Response:
    {
        "envelope_id": "doc-a7f3b2c1",
        "anchor_id": "anchor-enterprise",
        "content": "## Enterprise Plan...",
        "entities": [...]
    }
    """
    content = storage.get_anchor_content(envelope_id, anchor_id)
    
    if not content:
        return jsonify({
            "error": f"Anchor '{anchor_id}' not found in envelope '{envelope_id}'"
        }), 404
    
    # Also get entities linked to this anchor
    entities = storage.get_entities_by_anchor(envelope_id, anchor_id)
    
    return jsonify({
        "envelope_id": envelope_id,
        "anchor_id": anchor_id,
        "content": content,
        "entities": entities
    })


@app.route('/api/v1/entities', methods=['GET'])
def query_entities():
    """
    Query entities across all envelopes.
    
    Query params:
    - type: Filter by entity type (Product, PriceSpecification, etc.)
    - q: Search text in properties
    - limit: Max results (default 50)
    
    Examples:
    - GET /api/v1/entities?type=Product
    - GET /api/v1/entities?type=PriceSpecification&q=299
    - GET /api/v1/entities?q=enterprise
    """
    entity_type = request.args.get('type')
    query = request.args.get('q')
    limit = int(request.args.get('limit', 50))
    
    if query:
        entities = storage.search_entities(query, entity_type, limit)
    elif entity_type:
        entities = storage.get_entities_by_type(entity_type, limit)
    else:
        return jsonify({"error": "Provide 'type' or 'q' parameter"}), 400
    
    return jsonify({
        "count": len(entities),
        "entities": entities
    })


@app.route('/api/v1/stats', methods=['GET'])
def get_stats():
    """Get storage statistics."""
    return jsonify(storage.get_stats())


@app.route('/api/v1/envelope/<envelope_id>', methods=['DELETE'])
def delete_envelope(envelope_id: str):
    """Delete an envelope and all its components."""
    deleted = storage.delete_envelope(envelope_id)
    
    if not deleted:
        return jsonify({"error": f"Envelope '{envelope_id}' not found"}), 404
    
    return jsonify({"deleted": envelope_id})


# n8n-friendly batch endpoint
@app.route('/api/v1/batch', methods=['POST'])
def batch_process():
    """
    Process multiple documents in one request.
    
    Request body:
    {
        "documents": [
            {"content": "...", "source": "doc1.pdf"},
            {"content": "...", "source": "doc2.pdf"}
        ],
        "content_type": "html"
    }
    
    Response:
    {
        "processed": 2,
        "results": [
            {"envelope_id": "...", "token_count": 856, ...},
            {"envelope_id": "...", "token_count": 432, ...}
        ]
    }
    """
    data = request.get_json()
    
    if not data or 'documents' not in data:
        return jsonify({"error": "Missing 'documents' array"}), 400
    
    documents = data['documents']
    content_type = data.get('content_type', 'html')
    
    results = []
    for doc in documents:
        try:
            content = doc.get('content', '')
            source = doc.get('source', 'unknown')
            
            if content_type == 'html':
                result = pipeline.process_with_report(content, source, 'web')
            else:
                envelope = pipeline.process_markdown(content, source, 'markdown')
                result = {"envelope": envelope}
            
            envelope = result['envelope']
            storage.store_envelope(envelope)
            
            results.append({
                "envelope_id": envelope.id,
                "source": source,
                "token_count": envelope.narrative.token_count,
                "noise_score": envelope.narrative.noise_score,
                "anchors": len(envelope.anchors),
                "entities": len(envelope.entities),
                "status": "success"
            })
        except Exception as e:
            results.append({
                "source": doc.get('source', 'unknown'),
                "status": "error",
                "error": str(e)
            })
    
    return jsonify({
        "processed": len([r for r in results if r['status'] == 'success']),
        "failed": len([r for r in results if r['status'] == 'error']),
        "results": results
    })


if __name__ == '__main__':
    port = int(os.environ.get('ECR_PORT', 5000))
    debug = os.environ.get('ECR_DEBUG', 'false').lower() == 'true'
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║           ECR API Server - Entropy-Controlled Retrieval   ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Endpoints:                                               ║
    ║    POST /api/v1/process     - Process content             ║
    ║    POST /api/v1/batch       - Batch process               ║
    ║    GET  /api/v1/envelope/ID - Get envelope                ║
    ║    GET  /api/v1/anchor/ID/A - Get anchor content          ║
    ║    GET  /api/v1/entities    - Query entities              ║
    ║    GET  /api/v1/stats       - Storage stats               ║
    ║    GET  /health             - Health check                ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Running on: http://localhost:{port}                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=port, debug=debug)
