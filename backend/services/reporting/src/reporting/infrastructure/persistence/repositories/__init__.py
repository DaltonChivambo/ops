"""Repositórios de reporting.

Classes concretas que **recebem** a Session — nunca criam a sua. É isso que permite a um caso
de uso escrever em dois repositórios atomicamente sem precisar de Unit of Work.

    class TicketsRepository:
        def __init__(self, session: AsyncSession) -> None:
            self.session = session
"""
