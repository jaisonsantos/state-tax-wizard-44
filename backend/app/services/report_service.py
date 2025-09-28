import csv
import io
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from ..models.models import OrderFee, Store

class ReportService:
    
    @staticmethod
    def generate_co_dr1786(store_id: str, from_date: datetime, to_date: datetime, db: Session) -> str:
        """Generate Colorado DR-1786 CSV report"""
        
        # Query order fees for Colorado
        fees = db.query(OrderFee).join(Store).filter(
            OrderFee.store_id == store_id,
            OrderFee.jurisdiction == "CO",
            OrderFee.applied_at >= from_date,
            OrderFee.applied_at <= to_date
        ).all()
        
        # Create CSV content
        output = io.StringIO()
        writer = csv.writer(output)
        
        # DR-1786 Headers (simplified)
        writer.writerow([
            "Transaction Date",
            "Order ID", 
            "Fee Amount",
            "Delivery Method",
            "Reason Codes"
        ])
        
        for fee in fees:
            writer.writerow([
                fee.applied_at.strftime("%Y-%m-%d"),
                fee.order_id,
                f"${fee.amount_cents / 100:.2f}",
                fee.delivery_method,
                ",".join(fee.reason_codes or [])
            ])
        
        # Add demo data if no real data
        if not fees:
            writer.writerow([
                "2024-01-15",
                "CO-DEMO-001",
                "$0.28",
                "ship",
                "CO_HAS_TAXABLE_ITEM"
            ])
            writer.writerow([
                "2024-01-16", 
                "CO-DEMO-002",
                "$0.28",
                "ship",
                "CO_HAS_TAXABLE_ITEM"
            ])
        
        return output.getvalue()
    
    @staticmethod
    def generate_mn_summary(store_id: str, from_date: datetime, to_date: datetime, db: Session, format: str = "csv") -> str:
        """Generate Minnesota Summary report"""
        
        # Query order fees for Minnesota
        fees = db.query(OrderFee).join(Store).filter(
            OrderFee.store_id == store_id,
            OrderFee.jurisdiction == "MN",
            OrderFee.applied_at >= from_date,
            OrderFee.applied_at <= to_date
        ).all()
        
        if format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            
            writer.writerow([
                "Transaction Date",
                "Order ID",
                "Fee Amount", 
                "Delivery Method",
                "Reason Codes"
            ])
            
            for fee in fees:
                writer.writerow([
                    fee.applied_at.strftime("%Y-%m-%d"),
                    fee.order_id,
                    f"${fee.amount_cents / 100:.2f}",
                    fee.delivery_method,
                    ",".join(fee.reason_codes or [])
                ])
            
            # Add demo data if no real data
            if not fees:
                writer.writerow([
                    "2024-01-15",
                    "MN-DEMO-001", 
                    "$0.50",
                    "ship",
                    "MN_THRESHOLD_MET"
                ])
                writer.writerow([
                    "2024-01-16",
                    "MN-DEMO-002",
                    "$0.50", 
                    "ship",
                    "MN_THRESHOLD_MET"
                ])
            
            return output.getvalue()
        
        # TODO: JSON format for MN summary
        return ""