#!/usr/bin/env python3
"""
Example script demonstrating the markdown chunking functionality.
"""

from chunking import chunk_markdown

def main():
    # Example markdown content with various elements
    markdown_content = """# Introduction to AI
This is the introduction paragraph that explains what artificial intelligence is and why it matters.

## Machine Learning Basics
Machine learning is a subset of AI that focuses on algorithms.

Here's a simple example:

```python
def train_model(data):
    # This is a code block that should stay together
    model = LinearRegression()
    model.fit(data)
    return model
```

### Key Concepts
Here are the important concepts to understand:

- Supervised learning
- Unsupervised learning
- Reinforcement learning

Each of these has different applications and use cases.

## Performance Metrics
Different metrics are used to evaluate models:

| Metric    | Use Case           | Formula        |
|-----------|-------------------|----------------|
| Accuracy  | Classification    | TP+TN/Total   |
| Precision | Classification    | TP/(TP+FP)    |
| Recall    | Classification    | TP/(TP+FN)    |
| F1-Score  | Classification    | 2*P*R/(P+R)   |
| MSE       | Regression        | Σ(y-ŷ)²/n     |

This table shows common metrics used in machine learning evaluation.

## Conclusion
Machine learning is a powerful tool that continues to evolve and find new applications across industries.
"""

    print("Original content length:", len(markdown_content))
    print("\n" + "="*50)
    
    # Test different chunk sizes
    chunk_sizes = [200, 400, 800]
    
    for size in chunk_sizes:
        print(f"\nChunking with max size: {size} characters")
        print("-" * 40)
        
        chunks = chunk_markdown(markdown_content, size)
        
        print(f"Number of chunks: {len(chunks)}")
        
        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i} (length: {len(chunk)}):")
            print("┌" + "─" * 50 + "┐")
            
            # Show first few lines of each chunk
            lines = chunk.split('\n')
            for j, line in enumerate(lines[:5]):
                print(f"│ {line:<48} │")
            
            if len(lines) > 5:
                print(f"│ ... ({len(lines)-5} more lines) {'':<25} │")
            
            print("└" + "─" * 50 + "┘")
    
    print("\n" + "="*50)
    print("Demonstration complete!")

if __name__ == "__main__":
    main()
