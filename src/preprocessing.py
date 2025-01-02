from abc import ABC, abstractmethod


class PreprocessingStrategy(ABC):
    @abstractmethod
    def load_data():
        pass

    @abstractmethod
    def preprocess_data():
        pass


class PDFExtractor(PreprocessingStrategy):
    def load_data(self):
        pass


def main():
    raise NotImplementedError


if __name__ == "__main__":
    main()
