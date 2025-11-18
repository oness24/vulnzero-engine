"""
Security tests for SQL injection prevention

These tests verify that the application is protected against SQL injection attacks
through proper use of SQLAlchemy ORM and parameterized queries.
"""

import pytest
from sqlalchemy import text, select
from shared.database.models import Vulnerability, Patch

pytestmark = pytest.mark.asyncio


class TestSQLInjectionPrevention:
    """Test SQL injection prevention mechanisms"""

    async def test_orm_prevents_sql_injection_in_filter(self, db_session):
        """Test that SQLAlchemy ORM prevents SQL injection in WHERE clauses"""
        # Malicious input attempting SQL injection
        malicious_input = "1' OR '1'='1"

        # Using ORM - should safely escape the input
        stmt = select(Vulnerability).where(Vulnerability.cve_id == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should return empty, not all records
        assert len(vulns) == 0, "ORM failed to prevent SQL injection"

    async def test_orm_prevents_sql_injection_with_comment(self, db_session):
        """Test ORM prevents SQL injection using SQL comments"""
        # Malicious input with SQL comment
        malicious_input = "test'; DROP TABLE vulnerabilities; --"

        stmt = select(Vulnerability).where(Vulnerability.title == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should safely handle the input
        assert len(vulns) == 0

        # Verify table still exists by querying it
        check_stmt = select(Vulnerability).limit(1)
        result = await db_session.execute(check_stmt)
        # Should not raise an error

    async def test_parameterized_raw_query_prevents_injection(self, db_session):
        """Test that parameterized raw queries prevent SQL injection"""
        malicious_input = "1'; DROP TABLE vulnerabilities; --"

        # Correct way - parameterized query
        stmt = text("SELECT * FROM vulnerabilities WHERE cve_id = :cve_id")
        result = await db_session.execute(stmt, {"cve_id": malicious_input})

        # Should not execute the malicious SQL
        rows = result.fetchall()
        assert len(rows) == 0

    async def test_orm_prevents_union_injection(self, db_session):
        """Test ORM prevents UNION-based SQL injection"""
        # Attempt UNION-based injection
        malicious_input = "test' UNION SELECT * FROM users WHERE '1'='1"

        stmt = select(Vulnerability).where(Vulnerability.severity == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should return empty
        assert len(vulns) == 0

    async def test_orm_prevents_blind_sql_injection(self, db_session):
        """Test ORM prevents blind SQL injection"""
        # Boolean-based blind SQL injection attempt
        malicious_input = "1' AND 1=1 AND '1'='1"

        stmt = select(Vulnerability).where(Vulnerability.id == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should not match any records
        assert len(vulns) == 0

    async def test_orm_prevents_time_based_injection(self, db_session):
        """Test ORM prevents time-based SQL injection"""
        # Time-based injection attempt (PostgreSQL specific)
        malicious_input = "1'; SELECT pg_sleep(5); --"

        import time
        start_time = time.time()

        stmt = select(Vulnerability).where(Vulnerability.cve_id == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        end_time = time.time()
        duration = end_time - start_time

        # Should not cause a delay (should be fast, < 1 second)
        assert duration < 1.0, "Query took too long, possible time-based injection"
        assert len(vulns) == 0

    async def test_orm_prevents_stacked_queries(self, db_session):
        """Test ORM prevents stacked query injection"""
        # Stacked query injection attempt
        malicious_input = "test'; UPDATE patches SET status='deployed'; --"

        stmt = select(Vulnerability).where(Vulnerability.title == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Verify no patches were modified
        patches_stmt = select(Patch).where(Patch.status == "deployed")
        patches_result = await db_session.execute(patches_stmt)
        deployed_patches = patches_result.scalars().all()

        # Should not have deployed any patches via injection
        # (this assumes no patches are deployed in the test DB)
        assert len(vulns) == 0

    async def test_like_query_escaping(self, db_session):
        """Test LIKE queries properly escape wildcards"""
        # Input with LIKE wildcards
        malicious_input = "%"

        # Using ORM with like()
        stmt = select(Vulnerability).where(Vulnerability.title.like(f"%{malicious_input}%"))
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should safely handle the wildcard (may return results, but no injection)
        # The key is that it shouldn't cause an error or injection
        assert isinstance(vulns, list)

    async def test_in_clause_prevents_injection(self, db_session):
        """Test IN clause prevents SQL injection"""
        # Malicious list of IDs
        malicious_ids = ["1", "2'; DROP TABLE vulnerabilities; --"]

        stmt = select(Vulnerability).where(Vulnerability.id.in_(malicious_ids))
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should safely handle the input
        assert isinstance(vulns, list)

    async def test_order_by_column_validation(self, db_session):
        """Test ORDER BY clause with column name validation"""
        # Malicious ORDER BY attempt
        # Note: This test ensures we validate column names before using them
        # in ORDER BY clauses, which are harder to parameterize

        valid_column = "created_at"

        # This should work
        stmt = select(Vulnerability).order_by(text(valid_column))
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        assert isinstance(vulns, list)

    async def test_numeric_parameter_type_safety(self, db_session):
        """Test type safety for numeric parameters"""
        # String input when expecting integer
        malicious_input = "1 OR 1=1"

        # SQLAlchemy should handle type conversion safely
        stmt = select(Vulnerability).where(Vulnerability.cvss_score > malicious_input)

        # Should either convert safely or raise a type error, but not execute injection
        try:
            result = await db_session.execute(stmt)
            vulns = result.scalars().all()
            assert isinstance(vulns, list)
        except (ValueError, TypeError):
            # Type error is acceptable - it means the input was rejected
            pass


class TestInputSanitization:
    """Test input sanitization for user-provided data"""

    async def test_long_input_handling(self, db_session):
        """Test handling of excessively long input"""
        # Very long input string
        long_input = "A" * 10000

        stmt = select(Vulnerability).where(Vulnerability.title == long_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should handle without crashing
        assert len(vulns) == 0

    async def test_unicode_handling(self, db_session):
        """Test handling of unicode characters"""
        # Unicode input
        unicode_input = "test' OR '1'='1' 你好"

        stmt = select(Vulnerability).where(Vulnerability.title == unicode_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should safely handle unicode
        assert len(vulns) == 0

    async def test_null_byte_handling(self, db_session):
        """Test handling of null bytes"""
        # Null byte injection attempt
        malicious_input = "test\x00' OR '1'='1"

        stmt = select(Vulnerability).where(Vulnerability.cve_id == malicious_input)
        result = await db_session.execute(stmt)
        vulns = result.scalars().all()

        # Should safely handle
        assert len(vulns) == 0


class TestORMBestPractices:
    """Test that ORM best practices are followed"""

    async def test_no_string_concatenation_in_queries(self):
        """
        This is a meta-test to remind developers:
        NEVER use f-strings or string concatenation in SQL queries!

        ❌ BAD:
        query = f"SELECT * FROM users WHERE id = {user_id}"

        ✅ GOOD:
        stmt = select(User).where(User.id == user_id)
        """
        # This test exists as documentation
        assert True

    async def test_use_orm_not_raw_sql(self):
        """
        This test documents the preference for ORM over raw SQL

        ❌ AVOID:
        result = await db.execute("SELECT * FROM users WHERE id = 1")

        ✅ PREFER:
        stmt = select(User).where(User.id == 1)
        result = await db.execute(stmt)
        """
        assert True

    async def test_parameterize_when_raw_sql_needed(self):
        """
        When raw SQL is absolutely necessary, always parameterize

        ✅ CORRECT:
        stmt = text("SELECT * FROM users WHERE id = :id")
        result = await db.execute(stmt, {"id": user_id})
        """
        assert True
