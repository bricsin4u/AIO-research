package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// ContentEnvelope represents the standardized AIO output
type ContentEnvelope struct {
	ID        string  `json:"id"`
	SourceURL string  `json:"source_url"`
	Narrative string  `json:"narrative"`
	Tokens    int     `json:"tokens"`
	Items     []Chunk `json:"items,omitempty"`
}

// Chunk represents a single content piece from .aio
type Chunk struct {
	ID      string `json:"id"`
	Content string `json:"content"`
	Hash    string `json:"hash"`
}

// AIOTag represents the JSON structure of .aio files
type AIOFile struct {
	Version string  `json:"aio_version"`
	Content []Chunk `json:"content"`
	Index   []struct {
		ID       string   `json:"id"`
		Keywords []string `json:"keywords"`
	} `json:"index"`
}

func main() {
	fmt.Println("AIO Go Parser (Prototype)")
	fmt.Println("---------------------------")

	url := "http://localhost:8000"
	fmt.Printf("Fetching: %s\n", url)

	result, err := Parse(url, "pricing")
	if err != nil {
		fmt.Printf("Error: %v\n", err)
		return
	}

	fmt.Printf("Success! Retrieved %d tokens.\n", result.Tokens)
	fmt.Printf("Narrative Preview:\n%s...\n", result.Narrative[:100])
}

// Parse attempts to fetch AIO content, falling back to basic scraping
func Parse(url string, query string) (*ContentEnvelope, error) {
	// 1. Discovery (Simplified for prototype: Check direct URL)
	// Real implementation would check Link headers etc.
	aioURL := strings.TrimRight(url, "/") + "/ai-content.aio"
	
	resp, err := http.Get(aioURL)
	if err == nil && resp.StatusCode == 200 {
		defer resp.Body.Close()
		return parseAIO(resp.Body, url, query)
	}

	// 2. Fallback
	return nil, fmt.Errorf("fallback scraper not implemented in prototype yet")
}

func parseAIO(r io.Reader, sourceURL string, query string) (*ContentEnvelope, error) {
	var aio AIOFile
	if err := json.NewDecoder(r).Decode(&aio); err != nil {
		return nil, err
	}

	var narrativeBuilder strings.Builder
	var selectedChunks []Chunk

	// Targeted retrieval logic
	keywords := strings.Fields(strings.ToLower(query))
	
	for _, chunk := range aio.Content {
		matches := false
		if query == "" {
			matches = true
		} else {
			// Check index for keywords
			for _, idx := range aio.Index {
				if idx.ID == chunk.ID {
					for _, k := range idx.Keywords {
						for _, q := range keywords {
							if strings.Contains(strings.ToLower(k), q) {
								matches = true
								break
							}
						}
					}
					// Also check ID
					if strings.Contains(strings.ToLower(chunk.ID), keywords[0]) {
						matches = true
					}
				}
			}
		}

		if matches {
			selectedChunks = append(selectedChunks, chunk)
			narrativeBuilder.WriteString(chunk.Content)
			narrativeBuilder.WriteString("\n\n")
		}
	}

	narrative := narrativeBuilder.String()

	return &ContentEnvelope{
		ID:        fmt.Sprintf("aio-%d", time.Now().Unix()),
		SourceURL: sourceURL,
		Narrative: narrative,
		Tokens:    len(narrative) / 4,
		Items:     selectedChunks,
	}, nil
}
