from abc import ABC, abstractmethod

from monitaudit.models import BaseLog


class Sink(ABC):

    @abstractmethod
    def write(self, log: BaseLog) -> None:
        pass