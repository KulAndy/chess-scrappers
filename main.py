import multiprocessing
import chessarbiter_scrapper
import chessbase_scrapper
import chessmanager_scrapper
import chessresults_scrapper
import media_ichess_scrapper

if __name__ == '__main__':
    processes = [
        multiprocessing.Process(target=chessmanager_scrapper.main),
        multiprocessing.Process(target=chessresults_scrapper.main),
        multiprocessing.Process(target=chessbase_scrapper.main),
        multiprocessing.Process(target=media_ichess_scrapper.main),
    ]

    chessarbiter_scrapper.main()

    for process in processes:
        process.start()

    for process in processes:
        process.join()
