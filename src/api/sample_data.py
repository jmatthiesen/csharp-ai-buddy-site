#!/usr/bin/env python3
"""
Script to populate the MongoDB database with sample data for testing.
Run this script to add sample C# project data to the samples collection.
"""

import os
import json
import uuid
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample data following the schema
SAMPLE_DATA = [
    {
        "id": str(uuid.uuid4()),
        "title": ".NET + Semantic Search + AI Search - eShopLite",
        "description": "eShopLite - Semantic Search - Azure AI Search is a reference .NET application implementing an eCommerce site with advanced search capabilities using semantic search and Azure AI services.",
        "preview": "./templates/images/sample-eshop.png",
        "authorUrl": "https://github.com/BrunoCapuano",
        "author": "Bruno Capuano",
        "source": "https://github.com/Microsoft/eshoplite-semantic-search",
        "tags": ["AI", "Azure AI Search", "Azure SQL", "Bicep", ".NET/C#", "JavaScript", "Azure Log Analytics", "Azure Managed Identities", "Azure OpenAI Service", "TypeScript", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "WordPress with Azure Container Apps",
        "description": "A blueprint to easily and quickly create and deploy your first scalable and secure WordPress site to Azure, leveraging Azure Container Apps with Azure Database for MariaDB.",
        "preview": "./templates/images/apptemplate-wordpress-on-ACA.png",
        "authorUrl": "https://github.com/kpantos",
        "author": "Konstantinos Pantos",
        "source": "https://github.com/Azure-Samples/apptemplate-wordpress-on-ACA",
        "tags": ["bicep", "msft", "Azure Container Apps", "WordPress", "MariaDB"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Blazor Server Chat with SignalR",
        "description": "A real-time chat application built with Blazor Server and SignalR, demonstrating real-time communication in .NET applications with modern web UI patterns.",
        "preview": "./templates/images/blazor-chat.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft .NET Team",
        "source": "https://github.com/dotnet-samples/blazor-signalr-chat",
        "tags": [".NET/C#", "Blazor", "SignalR", "Real-time", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Minimal API with Entity Framework Core",
        "description": "A simple yet powerful example of building RESTful APIs using .NET Minimal APIs with Entity Framework Core for data access and modern authentication patterns.",
        "preview": "./templates/images/minimal-api.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft .NET Team",
        "source": "https://github.com/dotnet-samples/minimal-api-ef-core",
        "tags": [".NET/C#", "Entity Framework", "Minimal API", "REST", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Azure Functions with Cosmos DB",
        "description": "Serverless application demonstrating Azure Functions integration with Cosmos DB, including triggers, bindings, and best practices for cloud-native development.",
        "preview": "./templates/images/functions-cosmos.png",
        "authorUrl": "https://github.com/Azure",
        "author": "Azure Team",
        "source": "https://github.com/Azure-Samples/azure-functions-cosmosdb-csharp",
        "tags": [".NET/C#", "Azure Functions", "Cosmos DB", "Serverless", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "MAUI Cross-Platform App",
        "description": "Cross-platform mobile and desktop application built with .NET MAUI, showcasing native UI patterns across iOS, Android, Windows, and macOS from a single codebase.",
        "preview": "./templates/images/maui-app.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft .NET Team",
        "source": "https://github.com/dotnet-samples/maui-cross-platform",
        "tags": [".NET/C#", "MAUI", "Cross-platform", "Mobile", "Desktop", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "ASP.NET Core Web API with JWT",
        "description": "Secure Web API implementation using ASP.NET Core with JWT authentication, role-based authorization, and comprehensive API documentation with Swagger.",
        "preview": "./templates/images/webapi-jwt.png",
        "authorUrl": "https://github.com/community-dev",
        "author": "Community Developer",
        "source": "https://github.com/community-samples/aspnet-core-jwt-api",
        "tags": [".NET/C#", "ASP.NET Core", "JWT", "Authentication", "Web API", "Swagger"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "GraphQL API with Hot Chocolate",
        "description": "Modern GraphQL API built with Hot Chocolate framework, demonstrating schema-first development, real-time subscriptions, and efficient data fetching patterns.",
        "preview": "./templates/images/graphql-hotchocolate.png",
        "authorUrl": "https://github.com/ChilliCream",
        "author": "ChilliCream Team",
        "source": "https://github.com/ChilliCream/hotchocolate-examples",
        "tags": [".NET/C#", "GraphQL", "Hot Chocolate", "Schema-first", "Subscriptions"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Microservices with Docker",
        "description": "Microservices architecture example using .NET, Docker containers, API gateways, and service discovery patterns for building scalable distributed systems.",
        "preview": "./templates/images/microservices-docker.png",
        "authorUrl": "https://github.com/dotnet-architecture",
        "author": ".NET Architecture Team",
        "source": "https://github.com/dotnet-architecture/eShopOnContainers",
        "tags": [".NET/C#", "Microservices", "Docker", "Containers", "Architecture", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Clean Architecture Template",
        "description": "A comprehensive Clean Architecture solution template for .NET applications, including CQRS, Domain-Driven Design patterns, and extensive testing examples.",
        "preview": "./templates/images/clean-architecture.png",
        "authorUrl": "https://github.com/jasontaylordev",
        "author": "Jason Taylor",
        "source": "https://github.com/jasontaylordev/CleanArchitecture",
        "tags": [".NET/C#", "Clean Architecture", "CQRS", "DDD", "Testing", "Templates"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Xamarin to MAUI Migration",
        "description": "Step-by-step guide and example project showing how to migrate existing Xamarin.Forms applications to .NET MAUI with minimal code changes.",
        "preview": "./templates/images/xamarin-maui-migration.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft .NET Team",
        "source": "https://github.com/dotnet-samples/xamarin-to-maui-migration",
        "tags": [".NET/C#", "MAUI", "Xamarin", "Migration", "Mobile", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Orleans Distributed System",
        "description": "Distributed actor model application using Microsoft Orleans, demonstrating virtual actors, grain persistence, and building scalable cloud applications in .NET.",
        "preview": "./templates/images/orleans-actors.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft Orleans Team",
        "source": "https://github.com/dotnet-samples/orleans-distributed-sample",
        "tags": [".NET/C#", "Orleans", "Actors", "Distributed Systems", "Cloud", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Entity Framework Core Advanced",
        "description": "Advanced Entity Framework Core patterns including complex queries, performance optimization, change tracking, and database migrations in enterprise applications.",
        "preview": "./templates/images/ef-core-advanced.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft EF Team",
        "source": "https://github.com/dotnet-samples/ef-core-advanced-patterns",
        "tags": [".NET/C#", "Entity Framework", "Database", "Performance", "ORM", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "gRPC Services Example",
        "description": "High-performance gRPC services in .NET demonstrating binary protocols, streaming, authentication, and interoperability with other programming languages.",
        "preview": "./templates/images/grpc-services.png",
        "authorUrl": "https://github.com/grpc",
        "author": "gRPC Team",
        "source": "https://github.com/grpc-samples/dotnet-grpc-example",
        "tags": [".NET/C#", "gRPC", "Microservices", "Streaming", "Performance"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Machine Learning with ML.NET",
        "description": "Machine learning examples using ML.NET framework, including classification, regression, clustering, and recommendation systems with custom model training.",
        "preview": "./templates/images/mlnet-examples.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft ML.NET Team",
        "source": "https://github.com/dotnet-samples/mlnet-machine-learning",
        "tags": [".NET/C#", "ML.NET", "Machine Learning", "AI", "Data Science", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Blazor WebAssembly PWA",
        "description": "Progressive Web App built with Blazor WebAssembly, featuring offline capabilities, push notifications, and native-like mobile experiences using C#.",
        "preview": "./templates/images/blazor-pwa.png",
        "authorUrl": "https://github.com/dotnet",
        "author": "Microsoft Blazor Team",
        "source": "https://github.com/dotnet-samples/blazor-wasm-pwa",
        "tags": [".NET/C#", "Blazor", "WebAssembly", "PWA", "Offline", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Event Sourcing with EventStore",
        "description": "Event sourcing implementation using EventStore and .NET, demonstrating CQRS patterns, event versioning, and building event-driven architectures.",
        "preview": "./templates/images/event-sourcing.png",
        "authorUrl": "https://github.com/EventStore",
        "author": "EventStore Team",
        "source": "https://github.com/EventStore/samples-dotnet-event-sourcing",
        "tags": [".NET/C#", "Event Sourcing", "CQRS", "EventStore", "Architecture"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Azure Service Bus Messaging",
        "description": "Robust messaging patterns using Azure Service Bus with .NET, including queues, topics, dead letter handling, and reliable message processing.",
        "preview": "./templates/images/service-bus.png",
        "authorUrl": "https://github.com/Azure",
        "author": "Azure Team",
        "source": "https://github.com/Azure-Samples/azure-servicebus-messaging-dotnet",
        "tags": [".NET/C#", "Azure Service Bus", "Messaging", "Queues", "Topics", "msft"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Identity Server 4 OAuth",
        "description": "OAuth 2.0 and OpenID Connect server implementation using IdentityServer4, with client applications demonstrating secure authentication flows.",
        "preview": "./templates/images/identity-server.png",
        "authorUrl": "https://github.com/IdentityServer",
        "author": "IdentityServer Team",
        "source": "https://github.com/IdentityServer/IdentityServer4.Samples",
        "tags": [".NET/C#", "IdentityServer", "OAuth", "OpenID Connect", "Authentication"]
    },
    {
        "id": str(uuid.uuid4()),
        "title": "Redis Caching Strategies",
        "description": "Comprehensive Redis caching implementation with .NET, covering distributed caching, session storage, pub/sub messaging, and performance optimization.",
        "preview": "./templates/images/redis-caching.png",
        "authorUrl": "https://github.com/StackExchange",
        "author": "StackExchange Team",
        "source": "https://github.com/StackExchange/StackExchange.Redis.Samples",
        "tags": [".NET/C#", "Redis", "Caching", "Performance", "Distributed Systems"]
    }
]

def connect_to_mongodb():
    """Connect to MongoDB using environment variables."""
    mongodb_uri = os.getenv("MONGODB_URI")
    database_name = os.getenv("DATABASE_NAME")
    
    if not mongodb_uri:
        print("Error: MONGODB_URI environment variable is not set")
        return None, None
        
    if not database_name:
        print("Error: DATABASE_NAME environment variable is not set")
        return None, None
    
    try:
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        
        # Test the connection
        client.admin.command('ping')
        print(f"Successfully connected to MongoDB database: {database_name}")
        
        return client, db
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return None, None

def populate_samples_collection(db):
    """Populate the samples collection with test data."""
    try:
        samples_collection = db["samples"]
        
        # Clear existing samples (optional - comment out if you want to keep existing data)
        # samples_collection.delete_many({})
        # print("Cleared existing samples")
        
        # Insert sample data
        result = samples_collection.insert_many(SAMPLE_DATA)
        print(f"Successfully inserted {len(result.inserted_ids)} samples")
        
        # Create indexes for better performance
        samples_collection.create_index("id", unique=True)
        samples_collection.create_index("title")
        samples_collection.create_index("tags")
        samples_collection.create_index("author")
        print("Created database indexes")
        
        # Print summary
        total_samples = samples_collection.count_documents({})
        microsoft_samples = samples_collection.count_documents({"tags": "msft"})
        unique_tags = samples_collection.distinct("tags")
        
        print("\n=== Database Summary ===")
        print(f"Total samples: {total_samples}")
        print(f"Microsoft authored samples: {microsoft_samples}")
        print(f"Unique tags: {len(unique_tags)}")
        print(f"Tags: {', '.join(sorted(unique_tags))}")
        
        return True
        
    except Exception as e:
        print(f"Error populating samples collection: {e}")
        return False

def main():
    """Main function to populate the database."""
    print("C# AI Buddy - Samples Database Populator")
    print("=" * 50)
    
    # Connect to MongoDB
    client, db = connect_to_mongodb()
    if not client or not db:
        return False
    
    try:
        # Populate samples collection
        success = populate_samples_collection(db)
        
        if success:
            print("\n✅ Database population completed successfully!")
            print("\nYou can now test the samples gallery at:")
            print("  - Local: http://localhost:3000?tab=samples")
            print("  - Or open your frontend and click the 'Sample Gallery' tab")
        else:
            print("\n❌ Database population failed!")
            
        return success
        
    finally:
        # Close the connection
        client.close()
        print("\nMongoDB connection closed.")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)