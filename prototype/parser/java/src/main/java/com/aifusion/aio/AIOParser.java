package com.aifusion.aio;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.ArrayList;
import java.util.List;

public class AIOParser {
    private static final HttpClient client = HttpClient.newHttpClient();
    private static final ObjectMapper mapper = new ObjectMapper();

    public static void main(String[] args) {
        System.out.println("AIO Java Parser (Enterprise)");
        
        try {
            String url = "http://localhost:8000/ai-content.aio";
            System.out.println("Fetching: " + url);
            
            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(url))
                    .build();

            HttpResponse<String> response = client.send(request, HttpResponse.BodyHandlers.ofString());
            
            // Validate AIO
            JsonNode root = mapper.readTree(response.body());
            String version = root.path("aio_version").asText();
            System.out.println("AIO Version: " + version);
            
            // Targeted Search
            String query = "pricing";
            System.out.println("\nExecuting Enterprise Search: " + query);
            
            JsonNode content = root.path("content");
            List<String> results = new ArrayList<>();
            
            if (content.isArray()) {
                for (JsonNode chunk : content) {
                    String text = chunk.path("content").asText();
                    if (text.toLowerCase().contains(query)) {
                        results.add(text);
                    }
                }
            }
            
            System.out.println("Found " + results.size() + " matching chunks.");
            if (!results.isEmpty()) {
                System.out.println("Top Result: " + results.get(0).substring(0, 100) + "...");
            }
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
