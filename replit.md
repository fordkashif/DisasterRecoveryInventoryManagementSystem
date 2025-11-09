# Disaster Relief Inventory Management System (DRIMS)

## Overview
The Disaster Relief Inventory Management System (DRIMS) tracks and manages disaster relief supplies across multiple locations. Its purpose is to enhance disaster response efficiency and accountability by managing donations, recording distributions, monitoring stock in real-time, providing low-stock alerts, and tracking all transactions. The system aims to provide a robust solution for supply chain management in disaster relief operations.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Application Framework
Built with Flask (Python) for rapid development and deployment, utilizing SQLAlchemy ORM with a relational database design.

### Data Model
Key entities include Items, Depots, Donors, Beneficiaries, DisasterEvents, NeedsLists, and Transactions. Transactions are double-entry for stock calculation and audit trails. Items feature auto-generated SKUs, standardized units, barcode support, and expiry dates tracked at the transaction level. NeedsLists enable AGENCY hubs to request items from MAIN hubs with approval workflows.

### Barcode Scanning
Supports barcode scanning for efficient donation intake, reducing manual entry and errors.

### Needs List Management
Implements an end-to-end workflow for AGENCY and SUB hubs to request supplies, including preparation, approval, dispatch, and receipt confirmation. Logistics Officers and Managers have global visibility for orchestration and approval. A centralized permission system enforces role-based access control. The system ensures a complete audit trail for all actions.

### Distribution Package Management
Manages the creation, review, and approval of distribution packages for AGENCY hubs. It includes stock validation against available inventory across all ODPEM locations (MAIN and SUB hubs) and supports multi-depot fulfillment with smart allocation filtering and real-time stock updates. A comprehensive audit trail tracks the package lifecycle.

### Frontend Architecture
Uses server-side rendered HTML templates with Bootstrap 5 and Bootstrap Icons, focusing on quick deployment, minimal client-side dependencies, accessibility, and mobile-friendliness, incorporating Government of Jamaica branding.

### Stock Management
Stock levels are dynamically aggregated on-demand from transaction records. Comprehensive validation prevents negative stock levels during all inventory movements.

### Three-Tier Hub Orchestration System
Implements a role-based orchestration model with three hub types:
-   **MAIN Hub**: Central distribution, immediate transfers, approves requests from SUB/AGENCY hubs.
-   **SUB Hub**: Regional distribution, transfers require MAIN hub approval.
-   **AGENCY Hub**: Independent, requests items from MAIN hubs, inventory excluded from overall ODPEM displays.
The system features role-based governance, a transfer approval workflow based on hub type, and no parent hub assignments. AGENCY hub inventory is excluded from overall ODPEM displays to maintain separation.

### Stock Transfer with Approval Workflow
Enables stock transfers between depots with hub-based approval rules. MAIN hub users' transfers execute immediately, while SUB/AGENCY hub users' transfers create a TransferRequest for MAIN hub approval. An approval queue allows MAIN hub staff to review, approve, or reject requests, with real-time validation and a full audit trail.

### Dashboard Features
Provides a comprehensive overview with KPIs, inventory by category, stock by location, low stock alerts, recent transactions, expiring item alerts, activity by disaster event, and transaction analytics.

### Authentication and User Management
Implements Flask-Login with role-based access control (RBAC) for seven user roles: ADMIN, LOGISTICS_MANAGER, LOGISTICS_OFFICER, WAREHOUSE_STAFF, FIELD_PERSONNEL, EXECUTIVE, and AUDITOR. Features include secure password hashing, session management, role-aware navigation, and route protection. An ADMIN-only web interface manages user accounts. AGENCY hub users have a simplified navigation menu focused on Needs Lists and History.

### File Storage
Supports file attachments stored locally with UUID-based filenames, with a modular service for future cloud migration.

### Data Import/Export
Uses Pandas for CSV import and export, facilitating bulk data entry, spreadsheet integration, and data backup.

### Session Management
Utilizes Flask's built-in session handling with a secret key from environment variables.

## External Dependencies

### Core Framework Dependencies
-   **Flask**: 3.0.3
-   **Flask-SQLAlchemy**: 3.1.1
-   **SQLAlchemy**: 2.0.32

### Database Drivers
-   **psycopg2-binary**: For PostgreSQL.
-   **SQLite**: Built-in for development.

### Data Processing
-   **Pandas**: 2.2.2 (for CSV handling).

### Configuration Management
-   **python-dotenv**: 1.0.1 (for environment variables).

### Frontend Dependencies (CDN-delivered)
-   **Bootstrap**: 5.3.3
-   **Bootstrap Icons**: 1.11.3